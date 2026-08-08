#!/usr/bin/env python3
# Unit test for the pacific-now example skill script — demonstrates that Hermes skill
# scripts are tested in-repo (the "test" stage of the dev->deploy pipeline).
import importlib.util
import os
from datetime import datetime
from zoneinfo import ZoneInfo

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agents", "hermes", "skills", "examples", "pacific-now", "scripts", "pacific_now.py",
)
def _load():
    spec = importlib.util.spec_from_file_location("pacific_now", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
def test_formats_known_instant():
    mod = _load()
    # A fixed UTC instant -> Pacific (PST, UTC-8 in January).
    dt = datetime(2026, 1, 2, 3, 4, tzinfo=ZoneInfo("UTC"))
    out = mod.pacific_now_str(dt)
    assert out == "Thu 2026-01-01 19:04 PST", out
def test_default_now_is_pacific_string():
    mod = _load()
    out = mod.pacific_now_str()
    assert out.endswith(("PST", "PDT")), out
    assert len(out.split()) == 4, out
if __name__ == "__main__":
    test_formats_known_instant()
    test_default_now_is_pacific_string()
    print("ok")
