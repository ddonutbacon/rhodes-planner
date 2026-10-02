
from rhodes.core import profile_store


def test_profile_store_round_trip(tmp_path, monkeypatch):
    path = tmp_path / "profile.json"

    monkeypatch.setattr(profile_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(profile_store, "PROFILE_PATH", path)

    payload = {
        "inventory": {"lmd": 123},
        "goals": [{"operator": "Demo"}],
    }

    profile_store.save_profile(payload)
    assert profile_store.load_profile() == payload

    profile_store.clear_profile()
    assert profile_store.load_profile() == {}
