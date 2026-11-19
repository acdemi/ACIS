from io import StringIO

from rich.console import Console

from acis.observability.trace.types import Trace, TraceEvent
from acis.ui.demo_cases import DEMO_CASES
from acis.ui import tui


def test_tui_fixed_cases_use_the_shared_v1_inputs():
    fixed_cases = tui.DEMO_SCENARIOS[-len(DEMO_CASES) :]

    assert [item["query"] for item in fixed_cases] == [item["query"] for item in DEMO_CASES]
    assert all(item["fixture_mode"] for item in fixed_cases)
    assert all(item["intent"] == "diagnose" for item in fixed_cases)


def test_tui_trace_view_renders_actual_trace_id_and_events(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, force_terminal=False))
    trace = Trace(trace_id="trace-test-01", timestamp="2026-11-19T00:00:00Z")
    trace.append(
        TraceEvent(
            stage="memory",
            timestamp="2026-11-19T00:00:01Z",
            payload={"status": "success", "agent": "RAG"},
        )
    )

    tui._render_trace(trace)

    rendered = output.getvalue()
    assert "trace-test-01" in rendered
    assert "memory" in rendered
    assert "RAG" in rendered


def test_tui_history_shows_a_real_empty_state(monkeypatch):
    import acis.knowledge.storage.repository as repository

    output = StringIO()
    monkeypatch.setattr(repository, "list_decisions", lambda _limit: [])
    monkeypatch.setattr(tui, "console", Console(file=output, force_terminal=False))

    tui._render_history()

    assert "暂无历史诊断" in output.getvalue()


def test_tui_menu_discloses_demo_mode_and_history_trace_help(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(tui, "console", Console(file=output, force_terminal=False))
    monkeypatch.setattr(tui.Prompt, "ask", lambda *_args, **_kwargs: "q")

    assert tui._menu(False, False) == "q"
    rendered = output.getvalue()
    assert "DEMO / FIXTURE MODE" in rendered
    assert "[h] 历史" in rendered
    assert "[t] Trace" in rendered
    assert "[?] 帮助" in rendered

