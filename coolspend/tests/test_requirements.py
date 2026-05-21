"""
coolspend/tests/test_requirements.py — dependency-contract test for HF Spaces deploy.

Asserts that:
1. requirements.txt exists and pins every runtime import.
2. README.md opens with the Gradio Spaces YAML header (sdk: gradio, app_file, sdk_version).
3. The sdk_version in README matches the gradio== pin in requirements.txt (drift guard).
4. README documents both mock and live modes and mentions INFRARED_API_KEY.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# ── Resolve repo root (two levels up from coolspend/tests/) ─────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REQ_PATH = _REPO_ROOT / "requirements.txt"
_README_PATH = _REPO_ROOT / "README.md"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def req_text() -> str:
    assert _REQ_PATH.exists(), f"requirements.txt not found at {_REQ_PATH}"
    return _REQ_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def readme_text() -> str:
    assert _README_PATH.exists(), f"README.md not found at {_README_PATH}"
    return _README_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spaces_header(readme_text: str) -> str:
    """Extract the YAML front-matter block from README.md."""
    lines = readme_text.splitlines()
    # First non-empty line must be "---"
    non_empty = [l for l in lines if l.strip()]
    assert non_empty, "README.md is empty"
    assert non_empty[0].strip() == "---", (
        f"README.md first non-empty line must be '---' (YAML header start), "
        f"got: {non_empty[0]!r}"
    )
    # Collect lines between the first and second "---"
    header_lines: list[str] = []
    in_header = False
    close_count = 0
    for line in lines:
        if line.strip() == "---":
            close_count += 1
            if close_count == 1:
                in_header = True
                continue
            if close_count == 2:
                break
        if in_header:
            header_lines.append(line)
    return "\n".join(header_lines)


# ── requirements.txt contract ────────────────────────────────────────────────


def test_req_contains_pymoo_exact_pin(req_text: str) -> None:
    """pymoo==0.6.1 is a hard project constraint — must be exact."""
    assert "pymoo==0.6.1" in req_text, "requirements.txt must pin pymoo==0.6.1"


def test_req_contains_gradio(req_text: str) -> None:
    assert "gradio==" in req_text, "requirements.txt must pin gradio with '=='"


def test_req_contains_shapely(req_text: str) -> None:
    assert "shapely" in req_text, "requirements.txt must list shapely"


def test_req_contains_numpy(req_text: str) -> None:
    assert "numpy" in req_text, "requirements.txt must list numpy"


def test_req_contains_matplotlib(req_text: str) -> None:
    assert "matplotlib" in req_text, "requirements.txt must list matplotlib"


def test_req_contains_geojson(req_text: str) -> None:
    assert "geojson" in req_text, "requirements.txt must list geojson"


def test_req_contains_infrared_sdk(req_text: str) -> None:
    assert "infrared-sdk" in req_text, "requirements.txt must list infrared-sdk"


# ── README Spaces header contract ────────────────────────────────────────────


def test_readme_starts_with_yaml_header(spaces_header: str) -> None:
    """spaces_header fixture already asserts first non-empty line is '---'."""
    assert spaces_header, "README.md Spaces YAML header block is empty"


def test_readme_header_has_sdk_gradio(spaces_header: str) -> None:
    assert "sdk: gradio" in spaces_header, (
        "README.md Spaces header must contain 'sdk: gradio'"
    )


def test_readme_header_has_app_file(spaces_header: str) -> None:
    assert "app_file: coolspend/app.py" in spaces_header, (
        "README.md Spaces header must contain 'app_file: coolspend/app.py'"
    )


def test_readme_header_has_sdk_version(spaces_header: str) -> None:
    assert "sdk_version:" in spaces_header, (
        "README.md Spaces header must contain 'sdk_version:' line"
    )


# ── sdk_version / gradio== drift guard ───────────────────────────────────────


def _parse_gradio_pin(req_text: str) -> str:
    """Return the version string from 'gradio==X.Y.Z' in requirements.txt."""
    match = re.search(r"gradio==([^\s]+)", req_text)
    assert match, "Could not parse 'gradio==<version>' from requirements.txt"
    return match.group(1).strip()


def _parse_sdk_version(spaces_header: str) -> str:
    """Return the version string from 'sdk_version: X.Y.Z' in the Spaces header."""
    match = re.search(r"sdk_version:\s*([^\s]+)", spaces_header)
    assert match, "Could not parse 'sdk_version: <version>' from README.md Spaces header"
    return match.group(1).strip()


def test_sdk_version_matches_gradio_pin(req_text: str, spaces_header: str) -> None:
    """README sdk_version must equal the gradio== pin — prevents silent drift."""
    gradio_ver = _parse_gradio_pin(req_text)
    sdk_ver = _parse_sdk_version(spaces_header)
    assert gradio_ver == sdk_ver, (
        f"README sdk_version ({sdk_ver!r}) does not match "
        f"gradio== pin in requirements.txt ({gradio_ver!r}). "
        "Update one to make them consistent."
    )


# ── mock / live / key documentation ─────────────────────────────────────────


def test_readme_mentions_mock(readme_text: str) -> None:
    assert "mock" in readme_text.lower(), (
        "README.md must document the mock (offline) backend"
    )


def test_readme_mentions_live(readme_text: str) -> None:
    assert "live" in readme_text.lower(), (
        "README.md must document the live (real API) backend"
    )


def test_readme_mentions_infrared_api_key(readme_text: str) -> None:
    assert "INFRARED_API_KEY" in readme_text, (
        "README.md must mention INFRARED_API_KEY (Space Secret for live backend)"
    )
