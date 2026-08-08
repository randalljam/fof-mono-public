"""Tests for local instance discovery and icon resolution."""
import os
import sys
import tempfile

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import prism as prism_ops


def _write_instance(root, name, icon_key="test icon"):
    instance_dir = os.path.join(root, name)
    os.makedirs(instance_dir, exist_ok=True)
    with open(os.path.join(instance_dir, "instance.cfg"), "w", encoding="utf-8") as handle:
        handle.write("iconKey=" + icon_key + "\n")
        handle.write("name=" + name + "\n")


def test_discover_local_instances_sorted():
    with tempfile.TemporaryDirectory() as tmp:
        _write_instance(tmp, "Zulu Pack")
        _write_instance(tmp, "Alpha Pack")
        rows = prism_ops.discover_local_instances(instances_dir=tmp)
        names = [row["display_name"] for row in rows]
        assert names == ["Alpha Pack", "Zulu Pack"]


def test_icon_key_resolution_from_icons_dir():
    with tempfile.TemporaryDirectory() as tmp:
        icons_dir = os.path.join(tmp, "icons")
        instances_dir = os.path.join(tmp, "instances")
        os.makedirs(icons_dir)
        os.makedirs(instances_dir)
        icon_path = os.path.join(icons_dir, "alexs caves.png")
        with open(icon_path, "wb") as handle:
            handle.write(b"PNG")
        _write_instance(instances_dir, "Alex Pack", icon_key="alexs caves")
        resolved = prism_ops.resolve_icon_path("Alex Pack", instances_dir, icons_dir)
        assert resolved == icon_path


def test_icon_fallback_to_minecraft_icon():
    with tempfile.TemporaryDirectory() as tmp:
        instances_dir = os.path.join(tmp, "instances")
        icons_dir = os.path.join(tmp, "icons")
        os.makedirs(icons_dir)
        instance_dir = os.path.join(instances_dir, "Fallback Pack")
        os.makedirs(os.path.join(instance_dir, "minecraft"))
        _write_instance(instances_dir, "Fallback Pack", icon_key="missing")
        fallback = os.path.join(instance_dir, "minecraft", "icon.png")
        with open(fallback, "wb") as handle:
            handle.write(b"PNG")
        resolved = prism_ops.resolve_icon_path("Fallback Pack", instances_dir, icons_dir)
        assert resolved == fallback
