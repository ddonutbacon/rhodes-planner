from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = [ROOT / "app", ROOT / "rhodes"]


def test_no_dangerous_dynamic_execution_patterns():
    forbidden = [
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"pickle\.loads?\s*\(",
        r"yaml\.load\s*\(",
        r"os\.system\s*\(",
        r"shell\s*=\s*True",
    ]
    for directory in SOURCE_DIRS:
        for path in directory.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                assert not re.search(pattern, text), f"Forbidden pattern {pattern} in {path}"


def test_no_real_account_exports_bundled():
    suspicious = []
    for path in ROOT.rglob("*.json"):
        if path.name == "sample.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")[:20000]
        if '"troop"' in text and '"inventory"' in text and '"status"' in text:
            suspicious.append(path)
    assert suspicious == []


def test_portable_source_has_no_user_specific_absolute_windows_paths():
    patterns = [
        r"[A-Za-z]:\\Users\\",
        r"[A-Za-z]:\\ProgramData\\",
        r"\\Desktop\\",
        r"\\Downloads\\",
    ]
    checked = [ROOT / "app", ROOT / "rhodes", ROOT / "Rhodes Planner.bat"]
    for target in checked:
        paths = target.rglob("*") if target.is_dir() else [target]
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in {".py", ".bat"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                assert not re.search(pattern, text), f"Absolute/user-specific path {pattern} in {path}"


def test_portable_launcher_does_not_require_root_folder_named_portable():
    launcher = (ROOT / "Rhodes Planner.bat").read_text(encoding="utf-8", errors="ignore").lower()
    assert "%~dp0" in launcher
    assert "\\portable\\" not in launcher
    assert "portable\\runtime" not in launcher
