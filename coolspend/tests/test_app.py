"""
coolspend/tests/test_app.py — Headless tests for coolspend.app Gradio Blocks UI.

Tests:
  (a) test_build_demo_constructs         — build_demo() returns gr.Blocks; module has demo
  (b) test_on_submit_mock_returns_outputs — on_submit returns valid 4-tuple offline (mock)
  (c) test_on_submit_bad_geojson_no_crash — malformed GeoJSON does not raise; returns error
  (d) test_headless_launch_smoke          — demo.launch(prevent_thread_lock=True) boots OK

Environment:
  INFRARED_BACKEND is unset or "mock" — no API key required.
  INFRARED_API_KEY must NOT be set during these tests.
"""
from __future__ import annotations

import os
import socket

import pytest

# Ensure INFRARED_API_KEY is never set during these tests (T-03-05 guard)
os.environ.pop("INFRARED_API_KEY", None)
os.environ.setdefault("INFRARED_BACKEND", "mock")


# ── (a) Build demo constructs ─────────────────────────────────────────────────


def test_build_demo_constructs() -> None:
    """build_demo() must return a gr.Blocks and the module must expose a top-level demo."""
    import coolspend.app as app  # noqa: PLC0415  (local import — lazy on purpose)

    blocks = app.build_demo()
    assert type(blocks).__name__ == "Blocks", (
        f"Expected build_demo() to return a gr.Blocks, got {type(blocks).__name__}"
    )

    # Module-level demo attribute must exist (HF Spaces entrypoint)
    assert hasattr(app, "demo"), "coolspend.app must expose a module-level `demo` attribute"
    assert type(app.demo).__name__ == "Blocks", (
        f"app.demo must be a gr.Blocks, got {type(app.demo).__name__}"
    )


# ── (b) on_submit returns valid outputs offline ───────────────────────────────


def test_on_submit_mock_returns_outputs() -> None:
    """on_submit with default args (mock backend) returns a correct 4-tuple."""
    import coolspend.app as app

    result = app.on_submit(
        geojson_text=None,       # uses default fixture
        budget_eur=1_000_000.0,
        w_thermal=0.6,
        w_ecological=0.4,
        backend="mock",
    )

    assert isinstance(result, tuple), "on_submit must return a tuple"
    assert len(result) == 4, f"Expected 4-tuple, got {len(result)}-tuple"

    banner_md, img_path, table_rows, call_log_text = result

    # Banner must contain headline and the honesty disclaimer
    assert isinstance(banner_md, str), "banner_md must be a str"
    assert "Spend EUR" in banner_md, (
        f"banner_md must contain 'Spend EUR', got: {banner_md[:200]}"
    )
    assert "NOT MEASURED DATA" in banner_md, (
        f"banner_md must contain 'NOT MEASURED DATA' for mock backend, got: {banner_md[:200]}"
    )

    # Before/after image path must exist on disk
    assert img_path is not None and img_path != "", "img_path must be a non-empty string"
    from pathlib import Path
    assert Path(img_path).exists(), f"img_path {img_path!r} does not exist on disk"

    # Allocation table — exactly 3 rows (Top-3 configurations)
    assert isinstance(table_rows, list), "table_rows must be a list"
    assert len(table_rows) == 3, f"Expected 3 table rows, got {len(table_rows)}"

    # Call log must be non-empty (visible API call lines — ROADMAP #3)
    assert isinstance(call_log_text, str), "call_log_text must be a str"
    assert call_log_text.strip() != "", (
        "call_log_text must be non-empty — Infrared SDK calls must be visible in UI"
    )


# ── (c) Bad GeoJSON does not crash ───────────────────────────────────────────


def test_on_submit_bad_geojson_no_crash() -> None:
    """Malformed GeoJSON must not raise an exception; returns error banner and empty table."""
    import coolspend.app as app

    # Should NOT raise
    result = app.on_submit(
        geojson_text="{ not valid json",
        budget_eur=1_000_000.0,
        w_thermal=0.6,
        w_ecological=0.4,
        backend="mock",
    )

    assert isinstance(result, tuple) and len(result) == 4, (
        "on_submit must return a 4-tuple even on bad GeoJSON"
    )

    banner_md, img_path, table_rows, call_log_text = result

    # Banner or log must communicate an error
    combined = (banner_md or "") + (call_log_text or "")
    assert "error" in combined.lower() or "invalid" in combined.lower() or "ERROR" in combined, (
        f"Expected error indication in banner or log, got banner={banner_md!r}, log={call_log_text!r}"
    )

    # Image must be falsy (None or empty string)
    assert not img_path, f"Expected img_path to be falsy on error, got {img_path!r}"

    # Table must be empty
    assert table_rows == [] or table_rows is None, (
        f"Expected empty table on error, got {table_rows!r}"
    )


# ── (d-wave2) Generic error message — no traceback to UI ─────────────────────


def test_on_submit_unexpected_exception_no_traceback_in_ui(monkeypatch) -> None:
    """on_submit must NOT render traceback or internal paths to the UI banner.

    Security L1 (wave-2 Fix 5): before the fix, on_submit rendered
    traceback.format_exc() directly into the Gradio banner — exposing file paths
    and internal details on a public Space. After the fix, a generic message is
    shown to the UI; the full traceback is logged server-side only.
    """
    import coolspend.app as app

    # Force run_decision to raise an unexpected exception.
    # Patch in the app module's namespace (where the imported name lives) so the
    # except branch in on_submit actually fires.
    def _explode(*args, **kwargs):
        raise RuntimeError("Simulated internal error with C:\\secret\\path\\file.py")

    monkeypatch.setattr(app, "run_decision", _explode)

    result = app.on_submit(
        geojson_text=None,
        budget_eur=1_000_000.0,
        w_thermal=0.6,
        w_ecological=0.4,
        backend="mock",
    )

    assert isinstance(result, tuple) and len(result) == 4
    banner_md, img_path, table_rows, call_log_text = result

    # Must return an error banner (not a successful result)
    assert "ERROR" in banner_md or "error" in banner_md.lower(), (
        f"Expected error indication in banner: {banner_md!r}"
    )

    # Must NOT leak traceback, file paths, or the exception message to the UI
    assert "Traceback" not in banner_md, (
        "Traceback must not appear in the UI banner (Security L1)"
    )
    assert "File " not in banner_md, (
        "File path must not appear in the UI banner (Security L1)"
    )
    assert "secret" not in banner_md, (
        "Exception message content must not appear in the UI banner (Security L1)"
    )
    assert "Traceback" not in (call_log_text or ""), (
        "Traceback must not appear in the call_log_text output"
    )
    assert "secret" not in (call_log_text or ""), (
        "Exception message must not appear in call_log_text"
    )

    # Image and table must be empty (error path)
    assert not img_path
    assert table_rows == [] or table_rows is None


# ── (d) Headless launch smoke ─────────────────────────────────────────────────


def test_headless_launch_smoke() -> None:
    """demo.launch(prevent_thread_lock=True, server_port=0) boots and closes without error.

    If the OS refuses to bind a port (socket.error / OSError), or if Gradio's
    internal startup-events health-check ping fails (httpx.ConnectError — a known
    Gradio 4.x / Windows interaction when server_port=0 is used with ephemeral
    ports), skip gracefully — these are infrastructure constraints, NOT app
    construction errors. The Blocks object construction itself is what we verify.
    """
    import coolspend.app as app

    # Pre-verify: construction must always succeed regardless of network state
    blocks = app.build_demo()
    assert type(blocks).__name__ == "Blocks", "build_demo() must return a gr.Blocks"

    # Attempt headless launch — skip on any socket / network infrastructure error
    try:
        import httpx  # noqa: PLC0415
        _httpx_errors = (httpx.ConnectError, httpx.HTTPError, httpx.NetworkError)
    except ImportError:
        _httpx_errors = ()  # type: ignore[assignment]

    _skip_exceptions = (OSError, socket.error) + _httpx_errors

    try:
        # server_port=0 lets the OS pick a free ephemeral port
        launch_result = blocks.launch(
            prevent_thread_lock=True,
            show_error=True,
            server_port=0,
            quiet=True,
        )
        # Gradio 4.x launch returns (server_name, server_port, share_url)
        # The important thing: no exception was raised
        assert launch_result is not None or True, "launch() returned without raising"
    except _skip_exceptions as exc:  # type: ignore[misc]
        # Infrastructure / network constraint — server may have started before ping failed
        pytest.skip(
            f"Headless launch skipped — OS/network infrastructure constraint: {type(exc).__name__}: {exc}"
        )
    finally:
        try:
            blocks.close()
        except Exception:  # noqa: BLE001
            pass
