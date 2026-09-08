"""Offline tests. Nothing here touches a plug or the network."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load(monkeypatch=None):
    spec = importlib.util.spec_from_file_location("bm", ROOT / "battery-manager.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bm"] = module
    spec.loader.exec_module(module)
    return module


bm = load()
BASE = {"tapo_email": "a@b.c", "tapo_password": "x", "device_ip": "192.168.1.50"}


def write_config(cfg):
    path = Path(tempfile.mkdtemp()) / "config.json"
    path.write_text(json.dumps(cfg))
    bm.CONFIG_PATH = path
    return path


@pytest.mark.parametrize("ip,accepted", [
    ("192.168.1.50", True), ("10.0.0.5", True), ("172.16.0.1", True),
    ("127.0.0.1", True), ("169.254.1.1", True),
    ("8.8.8.8", False), ("1.1.1.1", False),
    ("example.com", False), ("192.168.1.999", False), ("", False),
])
def test_device_ip_must_be_private(ip, accepted):
    """Credentials must not be sendable to a host outside the local network."""
    write_config({**BASE, "device_ip": ip})
    if accepted:
        assert bm.load_config()["device_ip"]
    else:
        with pytest.raises(SystemExit):
            bm.load_config()


@pytest.mark.parametrize("extra,accepted", [
    ({}, True),
    ({"battery_min": "40"}, True),
    ({"battery_min": 40.0}, True),
    ({"battery_min": 40.9}, False),
    ({"battery_min": True}, False),
    ({"battery_min": "abc"}, False),
    ({"battery_min": None}, False),
    ({"battery_min": 80, "battery_max": 40}, False),
    ({"battery_min": 50, "battery_max": 50}, False),
    ({"battery_min": 0}, False),
    ({"battery_max": 101}, False),
])
def test_threshold_validation(extra, accepted):
    write_config({**BASE, **extra})
    if accepted:
        cfg = bm.load_config()
        assert 0 < cfg["battery_min"] < cfg["battery_max"] <= 100
    else:
        with pytest.raises(SystemExit):
            bm.load_config()


@pytest.mark.parametrize("name,accepted", [
    ("BAT0", True), (" BAT0 ", True), ("", False), (0, False), (None, False),
])
def test_battery_name_validation(name, accepted):
    write_config({**BASE, "battery_name": name})
    if accepted:
        assert bm.load_config()["battery_name"] == "BAT0"
    else:
        with pytest.raises(SystemExit):
            bm.load_config()


def test_placeholders_are_rejected():
    write_config({**BASE, "tapo_password": "YOUR_TAPO_ACCOUNT_PASSWORD"})
    with pytest.raises(SystemExit):
        bm.load_config()


def test_missing_config_is_rejected():
    bm.CONFIG_PATH = Path(tempfile.mkdtemp()) / "absent.json"
    with pytest.raises(SystemExit):
        bm.load_config()


def test_non_object_config_is_rejected():
    path = Path(tempfile.mkdtemp()) / "config.json"
    path.write_text("[1, 2, 3]")
    bm.CONFIG_PATH = path
    with pytest.raises(SystemExit):
        bm.load_config()


def test_example_config_is_valid_json_and_rejected_as_placeholder():
    cfg = json.loads((ROOT / "config.example.json").read_text())
    assert set(bm.REQUIRED_KEYS) <= set(cfg)
    write_config(cfg)
    with pytest.raises(SystemExit):
        bm.load_config()


def test_unknown_battery_exits_rather_than_guessing(tmp_path):
    """A missing battery must never fall through to 'charge on'."""
    bm.POWER_SUPPLY = tmp_path
    with pytest.raises(SystemExit):
        bm.battery_path({"battery_name": "BAT9"})


def test_upower_placeholder_line_is_ignored(tmp_path, monkeypatch):
    """upower prints '0% (should be ignored)' for devices it has not read."""
    (tmp_path / "BATX").mkdir()
    bm.POWER_SUPPLY = tmp_path

    class Result:
        stdout = "    percentage:          0% (should be ignored)\n"
        returncode = 0

    monkeypatch.setattr(bm.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(SystemExit):
        bm.get_battery_percent({"battery_name": "BATX"})


def test_upower_nonzero_exit_is_refused(tmp_path, monkeypatch):
    (tmp_path / "BATX").mkdir()
    bm.POWER_SUPPLY = tmp_path

    class Result:
        stdout = "    percentage:          42%\n"
        returncode = 1

    monkeypatch.setattr(bm.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(SystemExit):
        bm.get_battery_percent({"battery_name": "BATX"})


def test_upower_value_is_parsed(tmp_path, monkeypatch):
    (tmp_path / "BATX").mkdir()
    bm.POWER_SUPPLY = tmp_path

    class Result:
        stdout = "    percentage:          97.0981%\n"
        returncode = 0

    monkeypatch.setattr(bm.subprocess, "run", lambda *a, **k: Result())
    assert bm.get_battery_percent({"battery_name": "BATX"}) == 97
