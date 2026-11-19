from io import StringIO
from acis.observability.trace.types import Trace, TraceEvent
from types import SimpleNamespace

from rich.cells import cell_len
from rich.console import Console

from acis.ui import tui


def test_image_path_prompt_recovers_after_invalid_path(monkeypatch, tmp_path):
    image = tmp_path / "leaf photo.jpg"
    image.write_bytes(b"image fixture")
    answers = iter([str(tmp_path / "missing.jpg"), f'"{image}"'])
    output = StringIO()
    monkeypatch.setattr(tui.Prompt, "ask", lambda *_args, **_kwargs: next(answers))
    monkeypatch.setattr(tui, "console", Console(file=output, width=72, force_terminal=False))
    assert tui._prompt_image_path() == str(image.resolve())
    assert "找不到该文件" in output.getvalue()
    assert "检查路径" in output.getvalue()


def test_vision_status_discloses_mock_without_claiming_upload_or_model_success(monkeypatch, tmp_path):
    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, width=72, force_terminal=False))
    decision = SimpleNamespace(traces=[SimpleNamespace(agent="视觉Agent", execution={"status": "degraded", "mode": "mock", "model": None})])
    tui._render_vision_status(decision, str(tmp_path / "leaf.jpg"))
    rendered = output.getvalue()
    assert "图片路径已提供" in rendered
    assert "Mock" in rendered
    assert "并非真实模型推理" in rendered
    assert "上传成功" not in rendered


def test_trace_uses_readable_status_and_fits_narrow_terminal(monkeypatch):
    output = StringIO()
    terminal = Console(file=output, width=58, force_terminal=False)
    monkeypatch.setattr(tui, "console", terminal)
    trace = Trace(trace_id="narrow-trace", timestamp="2026-11-19T00:00:00Z")
    trace.append(TraceEvent(stage="perception", timestamp="2026-11-19T00:00:01Z", payload={"agent": "视觉Agent", "execution": {"status": "degraded", "mode": "mock", "duration_ms": 12}}))
    tui._render_trace(trace)
    rendered = output.getvalue()
    assert "narrow-trace" in rendered
    assert "降级 / Mock" in rendered
    assert "mock" in rendered
    assert all(cell_len(line) <= terminal.width for line in rendered.splitlines())


def test_abstention_report_uses_plain_language_and_requests_more_information(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, width=72, force_terminal=False))
    decision = SimpleNamespace(
        report={
            "status": "abstained",
            "confidence": {"band": "偏低", "score": 0.22, "meaning": "证据不足"},
            "follow_up_questions": ["请补充病斑近照"],
        }
    )

    tui._render_diagnosis_report(decision, None)

    rendered = output.getvalue()
    assert "弃权（证据不足）" in rendered
    assert "请补充病斑近照" in rendered


def test_success_report_uses_success_status_label(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, width=72, force_terminal=False))
    decision = SimpleNamespace(
        report={
            "status": "success",
            "crop": {"label": "玉米"},
            "confidence": {"band": "较高", "score": 0.82, "meaning": "证据较充分"},
            "diagnosis": "玉米大斑病",
        }
    )

    tui._render_diagnosis_report(decision, None)

    assert "诊断状态：成功" in output.getvalue()


def test_history_invalid_id_has_recovery_hint_in_narrow_terminal(monkeypatch):
    from acis.knowledge.storage import repository

    output = StringIO()
    terminal = Console(file=output, width=64, force_terminal=False)
    monkeypatch.setattr(tui, "console", terminal)
    monkeypatch.setattr(repository, "list_decisions", lambda _limit: [
        {"id": 42, "created_at": "2026-11-19", "crop": "maize", "confidence": 0.81, "decision": "玉米大斑病"}
    ])
    monkeypatch.setattr(tui.Prompt, "ask", lambda *_args, **_kwargs: "not-a-number")

    tui._render_history()

    rendered = output.getvalue()
    assert "记录 #42" in rendered
    assert "请输入数字记录 ID" in rendered


def test_compact_menu_keeps_primary_navigation(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, width=64, force_terminal=False))
    monkeypatch.setattr(tui.Prompt, "ask", lambda *_args, **_kwargs: "q")

    assert tui._menu(False, False) == "q"
    rendered = output.getvalue()
    assert "[x] 自定义" in rendered
    assert "[h] 历史" in rendered
    assert "[t] Trace" in rendered


def test_main_handles_terminal_eof_without_traceback(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, force_terminal=False))
    monkeypatch.setattr(tui, "_run_main", lambda: (_ for _ in ()).throw(EOFError()))

    tui.main()

    assert "安全退出" in output.getvalue()
    assert "Traceback" not in output.getvalue()


def test_failed_diagnosis_is_actionable_and_cleans_sensor_override(monkeypatch, caplog):
    from acis.reasoning.rule_engine import sensor_anomaly

    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, force_terminal=False))
    monkeypatch.setattr(tui, "build_context", lambda _query, image_path=None: SimpleNamespace(crop="maize", intent="diagnose"))

    class FailedOrchestrator:
        def run(self, _query, image_path=None):
            raise RuntimeError("private backend detail")

    monkeypatch.setattr(tui, "_get_orchestrator", lambda *_args: FailedOrchestrator())

    tui._run_scenario("病斑", False, False, {"humidity_offset": 5}, "错误恢复测试")

    rendered = output.getvalue()
    assert "本次未生成新的诊断结论" in rendered
    assert "检查输入" in rendered
    assert "private backend detail" not in rendered
    assert "gh-a" not in sensor_anomaly.ANOMALIES
    assert "RuntimeError" in caplog.text
    assert "private backend detail" not in caplog.text


def test_narrow_history_trace_keeps_trace_id_and_execution_state(monkeypatch):
    from acis.knowledge.storage import repository

    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, width=68, force_terminal=False))
    monkeypatch.setattr(repository, "list_decisions", lambda _limit: [
        {"id": 7, "created_at": "2026-11-19", "crop": "wheat", "confidence": 0.45, "decision": "需要鉴别"}
    ])
    monkeypatch.setattr(repository, "get_decision", lambda _decision_id: {
        "decision": "需要鉴别",
        "trace_id": "history-trace-7",
        "trace_json": {
            "trace_id": "history-trace-7",
            "events": [{
                "stage": "judge",
                "timestamp": "2026-11-19T00:00:01Z",
                "payload": {"status": "abstained", "agent": "Judge"},
            }],
        },
    })
    monkeypatch.setattr(tui.Prompt, "ask", lambda *_args, **_kwargs: "7")

    tui._render_history()

    rendered = output.getvalue()
    assert "history-trace-7" in rendered
    assert "judge" in rendered
    assert "弃权（证据不足）" in rendered


def test_run_scenario_passes_image_path_to_shared_orchestrator(monkeypatch, tmp_path):
    image = tmp_path / "leaf.png"
    image.write_bytes(b"image fixture")
    received = {}

    class FakeOrchestrator:
        last_trace = None

        def run(self, query, image_path=None):
            received.update(query=query, image_path=image_path)
            return SimpleNamespace(judge_analysis={}, judge_mode="rules", traces=[])

    monkeypatch.setattr(tui, "build_context", lambda _query, image_path=None: SimpleNamespace(crop="maize", intent="diagnose"))
    monkeypatch.setattr(tui, "_get_orchestrator", lambda *_args: FakeOrchestrator())
    monkeypatch.setattr(tui, "_render_result", lambda *_args, **_kwargs: None)
    tui._run_scenario("叶片出现病斑", False, False, None, "自定义查询", image_path=str(image))
    assert received == {"query": "叶片出现病斑", "image_path": str(image)}
