from __future__ import annotations

import importlib.util
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = ROOT / "app" / "launcher.py"

spec = importlib.util.spec_from_file_location("rhodes_portable_launcher", LAUNCHER_PATH)
launcher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(launcher)


def test_launcher_root_is_derived_from_launcher_file_not_cwd():
    assert launcher.root_dir() == ROOT


def test_choose_port_falls_back_when_8501_is_busy(monkeypatch):
    monkeypatch.setattr(launcher, "PREFERRED_PORT", 8501)
    monkeypatch.setattr(launcher, "MAX_PORT", 8503)
    monkeypatch.setattr(launcher, "port_is_available", lambda p: p == 8502)
    assert launcher.choose_port() == 8502


def test_port_availability_probe_returns_boolean():
    assert isinstance(launcher.port_is_available(0), bool)
