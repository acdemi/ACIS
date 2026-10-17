"""Phase 4.2 batch execution harness (216 direct API calls).

Executes the Phase 4.2 stability study as a standalone, controlled loop:

    for seed in [42, 43, 44]:
        set_seed(seed)  # random/numpy, and pass-through to the API call
        for config in ['C0', 'C1', 'C2']:
            for case_id in 1..24:
                prompt = build_prompt(case_id, config)
                response = call_deepseek_api(prompt, seed=seed)
                save_result(seed, config, case_id, prompt, response)

Prompt filling rules (see the Phase 4.2 audit spec, section 2):

| config | history_text      | retrieved_docs |
|--------|-------------------|----------------|
| C0     | "" (empty)        | "None"         |
| C1     | memory recall     | Qdrant top-3 + Neo4j |
| C2     | "" (forced empty) | Qdrant top-3 + Neo4j |

Constraints honored:
- No agent code is modified; the memory recall path reads
  ``agents.case_memory_agent`` (import-only) and the retrieval path reads
  ``rag.retriever.retrieve`` + ``kg_adapter.query_kg`` (call-only).
- The Challenge Set v1 file is only read.
- The scorer is not involved; ``coherence`` (1-5) is the model's own
  self-assessment, stored as-is.

Every call is logged under ``--log-dir`` (request meta: model, temperature,
seed param, endpoint, timestamp; response: status, latency, usage, raw
content) so the audit can verify seed pass-through. The aggregate raw
results (input prompt + output JSON + latency) are written to ``--output``.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _env import load_env
from decision_semantics import is_abstention, normalize_decision_label
from utils.judge_runtime import (
    classify_failure,
    redact_error_detail,
    resolve_judge_config,
)

#: Challenge set (read-only).
CHALLENGE_PATH = ROOT / "benchmarks" / "challenge_set_v1.json"


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()

#: Configurations accepted by the harness (mapped to prompt filling rules).
CONFIGS: tuple[str, ...] = ("C0", "C1", "C2")

#: Default seeds (Phase 4.2 spec).
DEFAULT_SEEDS: tuple[int, ...] = (42, 43, 44)

#: Default case range (1-24).
DEFAULT_CASES: tuple[int, int] = (1, 24)

#: Fallback model used only if the shared Judge resolver has no model set.
DEFAULT_MODEL: str = "deepseek-chat"

#: LLM sampling temperature (matches the system judge setting).
TEMPERATURE: float = 0.1

#: Retry budget for transient API failures.
MAX_ATTEMPTS: int = 3

SYSTEM_PROMPT = """You are ACIS (Agricultural Cognitive Intelligence System), a professional multi-agent diagnostic system.
Your role is to diagnose crop diseases, pests, and nutritional deficiencies based on provided evidence.
You must follow these principles:
- Base your diagnosis strictly on the evidence provided in the user query and retrieved knowledge.
- If evidence is insufficient or highly ambiguous, you must output "ABSTAIN" instead of guessing.
- Provide a confidence score (0.0-1.0) reflecting the strength of supporting evidence.
- Output must be valid JSON with keys: "diagnosis", "confidence", "coherence", "reasoning"."""

USER_PROMPT_TEMPLATE = """【Crop Environment】
- Crop Type: {crop}
- Growth Stage: {stage}
- Observation Date: {date}

【Symptoms Observed】
{description}

【Visual Clues (if any)】
{image_caption_features}

【Historical Diagnosis Context】
{history_text}

【Retrieved External Knowledge】
{retrieved_docs}

【Task Instruction】
Based on the above information, provide a diagnostic decision.
If the information is conflicting or insufficient to reach a confident conclusion, you MUST output "ABSTAIN".
Strictly output JSON format:
{{
  "diagnosis": "specific disease/pest name or ABSTAIN",
  "confidence": 0.xx,
  "coherence": integer (1-5, assessing internal logic of evidence),
  "reasoning": "brief chain-of-thought summary"
}}"""

#: Required keys of the model's JSON output (validated, not modified).
REQUIRED_KEYS: tuple[str, ...] = ("diagnosis", "confidence", "coherence", "reasoning")


def set_seed(seed: int) -> None:
    """Seed Python's ``random`` and, when available, numpy."""
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass


def load_cases() -> list[dict[str, Any]]:
    """Flatten the challenge set in group order; case ids are 1..24."""
    data = json.loads(CHALLENGE_PATH.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for spec in data.get("groups", {}).values():
        for case in spec.get("cases", []):
            cases.append(
                {
                    "case_id": len(cases) + 1,
                    "id": case["id"],
                    "group": case["group"],
                    "difficulty": case["difficulty"],
                    "input": case["input"],
                    "expected_key_factors": list(case["expected_key_factors"]),
                    "ground_truth": case.get("ground_truth"),
                    "crop": case.get("crop"),
                    "intent": case.get("intent"),
                }
            )
    return cases


def _crop_zh(crop: str) -> str:
    from rag.knowledge_base import CROP_MAP

    return CROP_MAP.get(crop.lower(), crop)


def build_history_text(case: dict[str, Any], config: str) -> str:
    """History filling per config: C1 recalls the memory layer (import-only
    use of the real agent); C0/C2 stay empty."""
    if config != "C1":
        return ""
    try:
        from agents.case_memory_agent import CaseMemoryAgent
        from agents.types import RequestContext

        context = RequestContext(
            query=str(case["input"]),
            greenhouse_id="温室A",
            crop=str(case["crop"]),
        )
        output = CaseMemoryAgent().run(context)
        return (
            f"最近3轮对话摘要：{output.claim}"
            + (
                f"（证据：{json.dumps(output.evidence, ensure_ascii=False)})"
                if output.evidence
                else ""
            )
        )
    except Exception as exc:  # noqa: BLE001  memory layer must never crash the harness
        return f"最近3轮对话摘要：记忆层不可用（{exc}）"


def build_retrieved_docs(case: dict[str, Any], config: str) -> str:
    """Retrieval filling per config: C0 forces "None"; C1/C2 pull Qdrant
    top-3 (memory fallback when Qdrant is down) + Neo4j entities via the
    frozen retrieval chain (call-only, no modification)."""
    if config == "C0":
        return "None"
    crop = str(case["crop"])
    query = str(case["input"])
    lines: list[str] = []
    try:
        from rag.retriever import retrieve

        hits = retrieve(query, crop=crop, top_k=3)
        for index, hit in enumerate(hits, start=1):
            lines.append(
                f"- [doc {index}] {hit.get('title', hit.get('name', ''))}: "
                f"{str(hit.get('content', hit.get('text', '')))[:200]}"
            )
    except Exception as exc:  # noqa: BLE001  retrieval fallback is a valid data point
        lines.append(f"- retrieval unavailable: {exc}")
    try:
        from kg_adapter import query_kg

        kg = query_kg(crop, query, top_k=3)
        triples = kg.get("triple_strings") or []
        for triple in triples[:6]:
            lines.append(f"- KG: {triple}")
        diseases = kg.get("diseases") or []
        if diseases:
            lines.append(f"- KG diseases: {', '.join(diseases)}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"- kg unavailable: {exc}")
    return "\n".join(lines) if lines else "None"


def build_prompt(case: dict[str, Any], config: str) -> str:
    """Assemble the user prompt per the Phase 4.2 filling table."""
    history = build_history_text(case, config)
    docs = build_retrieved_docs(case, config)
    return USER_PROMPT_TEMPLATE.format(
        crop=_crop_zh(str(case["crop"])),
        stage="未知",
        date=_today_iso(),
        description=str(case["input"]),
        image_caption_features="无",
        history_text=history,
        retrieved_docs=docs,
    )


def _seed_unsupported(exc: Exception) -> bool:
    """Return true only for a provider rejection attributable to ``seed``."""
    status = getattr(exc, "status_code", None)
    text = str(exc).lower()
    return status in {400, 422} and "seed" in text


def call_deepseek_api(
    prompt: str,
    *,
    seed: int,
    model: str,
    base_url: str,
    api_key: str,
    timeout_seconds: float = 60.0,
    max_retries: int = 0,
) -> dict[str, Any]:
    """Call the configured endpoint with one explicit retry-owner policy.

    The harness owns transient retries (``MAX_ATTEMPTS``).  The OpenAI SDK is
    configured with ``max_retries=0`` here so the two retry layers cannot
    multiply.  A request without ``seed`` is attempted only when the provider
    explicitly rejects ``seed``, and that fallback is recorded separately.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    started = time.perf_counter()
    attempt: int | None = None
    request_count = 0
    last_exc: Exception | None = None
    for attempt_index in range(1, MAX_ATTEMPTS + 1):
        attempt = attempt_index
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "response_format": {"type": "json_object"},
            "seed": seed,
        }
        seed_accepted = True
        try:
            try:
                request_count += 1
                resp = client.chat.completions.create(**kwargs)
            except Exception as exc:
                if not _seed_unsupported(exc):
                    raise
                seed_accepted = False
                kwargs.pop("seed", None)
                request_count += 1
                resp = client.chat.completions.create(**kwargs)
            latency = time.perf_counter() - started
            content = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)
            return {
                "status": "ok",
                "seed_accepted": seed_accepted,
                "latency_seconds": round(latency, 3),
                "content": content,
                "usage": {
                    "prompt_tokens": int(usage.prompt_tokens),
                    "completion_tokens": int(usage.completion_tokens),
                    "total_tokens": int(usage.total_tokens),
                }
                if usage is not None
                else None,
                "attempts": attempt,
                "request_count": request_count,
                "retry_count": max(0, request_count - 1),
                "failure_code": None,
            }
        except Exception as exc:  # noqa: BLE001 - classified below
            last_exc = exc
            retryable = classify_failure(exc) in {
                "connection_error", "timeout", "rate_limit", "server_error"
            }
            if retryable and attempt_index < MAX_ATTEMPTS:
                time.sleep(2 * attempt_index)
            else:
                break
    assert last_exc is not None
    return {
        "status": "error",
        "seed_accepted": False,
        "latency_seconds": round(time.perf_counter() - started, 3),
        "content": "",
        "usage": None,
        "error": redact_error_detail(last_exc, api_key=api_key),
        "attempts": attempt,
        "request_count": request_count,
        "retry_count": max(0, request_count - 1),
        "failure_code": classify_failure(last_exc),
    }


def parse_output(content: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse + schema-check the model output. Returns (parsed, error)."""
    try:
        parsed = json.loads(content)
    except Exception as exc:  # noqa: BLE001
        return None, f"invalid JSON: {exc}"
    if not isinstance(parsed, dict):
        return None, "output is not a JSON object"
    missing = [key for key in REQUIRED_KEYS if key not in parsed]
    if missing:
        return None, f"missing keys: {missing}"
    return parsed, None


def _sanitize(prompt: str) -> str:
    """Redact anything that looks like a credential from logged prompts."""
    import re

    return re.sub(r"(sk-[A-Za-z0-9_-]{8,})", "[REDACTED]", prompt)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env()
    runtime = resolve_judge_config()
    if not runtime.configured:
        print("error: Judge API key is not set")
        return 1
    api_key = runtime.api_key
    base_url = runtime.base_url
    model = runtime.model
    runtime_metadata = runtime.public_metadata()

    cases = load_cases()
    case_ids = _resolve_cases(args.cases)
    unknown = [cid for cid in case_ids if cid < 1 or cid > len(cases)]
    if unknown:
        print(f"error: case ids out of range: {unknown} (1-{len(cases)})")
        return 1
    selected = {case["case_id"]: case for case in cases}

    log_root = Path(args.log_dir)
    log_root.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    manifest = {
        **runtime_metadata,
        "temperature": TEMPERATURE,
        "retry_owner": "harness",
        "harness_max_attempts": MAX_ATTEMPTS,
        "configs": args.configs,
        "seeds": args.seeds,
        "case_ids": case_ids,
        "challenge_set": str(CHALLENGE_PATH),
        "execution_semantics": "direct_llm_baseline",
        "decision_semantics": "final_decision",
        "confidence_semantics": (
            "model self-assessment that the final diagnosis label is correct"
        ),
        "started": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Standalone Phase 4.2 harness: direct LLM API calls with the "
            "Phase 4.2 baseline prompt. This is a separate execution path "
            "from the real multi-agent ACIS Judge."
        ),
    }
    (log_root / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total = len(args.seeds) * len(args.configs) * len(case_ids)
    completed = 0
    for seed in args.seeds:
        set_seed(seed)
        for config in args.configs:
            for case_id in case_ids:
                case = selected[case_id]
                prompt = build_prompt(case, config)
                response = call_deepseek_api(
                    prompt,
                    seed=seed,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    timeout_seconds=runtime.timeout_seconds,
                    max_retries=0,
                )
                parsed, error = (
                    parse_output(response["content"])
                    if response["status"] == "ok"
                    else (None, response.get("error"))
                )
                decision = str((parsed or {}).get("diagnosis", ""))
                confidence = (parsed or {}).get("confidence")
                record = {
                    "seed": seed,
                    "config": config,
                    "case_id": case_id,
                    "case_label": case["id"],
                    "group": case["group"],
                    "difficulty": case["difficulty"],
                    "prompt": _sanitize(prompt),
                    "status": response["status"],
                    "seed_accepted": response["seed_accepted"],
                    "attempts": response.get("attempts"),
                    "request_count": response.get("request_count", 0),
                    "retry_count": response.get("retry_count", 0),
                    "failure_code": response.get("failure_code"),
                    "latency_seconds": response["latency_seconds"],
                    "usage": response["usage"],
                    "valid": parsed is not None,
                    "parse_error": error,
                    "output": parsed,
                    "decision": decision if parsed is not None else "",
                    "confidence": confidence,
                    "abstained": is_abstention(decision),
                    "decision_label": normalize_decision_label(
                        decision,
                        known_labels=tuple(
                            str(item.get("ground_truth"))
                            for item in cases
                            if item.get("ground_truth")
                        ),
                    ),
                    "judge_mode": "direct_llm" if parsed is not None else "unavailable",
                    "execution_semantics": "direct_llm_baseline",
                    "judge_runtime": {
                        **runtime_metadata,
                        "outcome": "success" if parsed is not None else "error",
                        "failure_code": response.get("failure_code"),
                        "request_count": response.get("request_count", 0),
                        "retry_count": response.get("retry_count", 0),
                        "retry_owner": "harness",
                    },
                    "raw_content": _sanitize(response["content"]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                results.append(record)
                # per-call audit log
                call_log = log_root / f"run_{seed}" / f"config_{config}" / (
                    f"case_{case_id:02d}.json"
                )
                call_log.parent.mkdir(parents=True, exist_ok=True)
                call_log.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                completed += 1
                print(
                    f"[{completed}/{total}] seed={seed} config={config} "
                    f"case={case_id:02d} status={response['status']} "
                    f"valid={parsed is not None} "
                    f"latency={response['latency_seconds']}s"
                )
                if completed % 25 == 0:
                    _write_aggregate(
                        output_path,
                        manifest,
                        results,
                        completed=completed,
                    )

    manifest["finished"] = datetime.now(timezone.utc).isoformat()
    manifest["completed_calls"] = completed
    (log_root / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_aggregate(output_path, manifest, results, completed=completed)
    print(f"phase 4.2 complete: {completed} calls -> {output_path}")
    return 0


def _write_aggregate(
    output_path: Path,
    manifest: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    completed: int,
) -> None:
    """Write the aggregate raw-results JSON (checkpoint-safe)."""
    manifest = dict(manifest)
    manifest["completed_calls"] = completed
    output_path.write_text(
        json.dumps({"manifest": manifest, "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _resolve_cases(spec: str) -> list[int]:
    """Parse '1-24' or '1,3,5-7' into a sorted unique case id list."""
    ids: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            ids.extend(range(int(start), int(end) + 1))
        else:
            ids.append(int(chunk))
    return sorted(set(ids))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 4.2 batch execution (216 direct API calls)"
    )
    parser.add_argument(
        "--configs",
        nargs="*",
        choices=CONFIGS,
        default=list(CONFIGS),
        help="configurations (default: C0 C1 C2)",
    )
    parser.add_argument(
        "--seeds",
        nargs="*",
        type=int,
        default=list(DEFAULT_SEEDS),
        help="seeds (default: 42 43 44)",
    )
    parser.add_argument(
        "--cases",
        default="1-24",
        help="case id range, e.g. '1-24' or '1,3,5-7' (default: 1-24)",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "phase4_2_raw_results.json"),
        help="aggregate raw results JSON path",
    )
    parser.add_argument(
        "--log-dir",
        default=str(ROOT / "logs" / "phase4_2"),
        help="per-call audit log directory",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
