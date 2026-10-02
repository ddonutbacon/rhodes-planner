from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_dangerous_dynamic_execution_in_app_code():
    forbidden = [
        "eval(",
        "exec(",
        "pickle.loads",
        "pickle.load(",
        "yaml.load(",
        "os.system(",
    ]

    files = list((ROOT / "rhodes").rglob("*.py")) + [ROOT / "app" / "main.py"]
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in files)

    for token in forbidden:
        assert token not in corpus
