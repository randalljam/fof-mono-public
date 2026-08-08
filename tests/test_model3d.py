# ===== START OF FILE tests/test_model3d.py =====
# Offline tests for the mesh -> Blender model3d scaffold.

import os
import sys
import json
import struct
import base64

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.content_studio.model3d import config, meshy, rodin
from apps.content_studio.model3d.validate_glb import parse_glb, validate_dragon_glb

### GLB fixture helpers
def build_glb_bytes(clips=None, bbox=None):
    """Build a minimal GLB fixture with one mesh, one skin, and named clips."""
    clips = clips or list(config.REQUIRED_CLIPS)
    bbox = bbox or {"min": [-10, 0, -5], "max": [10, 50, 5]}
    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3",
         "min": bbox["min"], "max": bbox["max"]},
        {"bufferView": 0, "componentType": 5123, "count": 6, "type": "SCALAR"},
    ]
    animations = []
    for clip in clips:
        input_index = len(accessors)
        output_index = input_index + 1
        accessors.append({"bufferView": 0, "componentType": 5126, "count": 2,
                          "type": "SCALAR", "min": [0.0], "max": [1.0]})
        accessors.append({"bufferView": 0, "componentType": 5126, "count": 2,
                          "type": "VEC3", "min": [0, 0, 0], "max": [0, 0, 0]})
        animations.append({
            "name": clip,
            "samplers": [{"input": input_index, "output": output_index, "interpolation": "LINEAR"}],
            "channels": [{"sampler": 0, "target": {"node": 1, "path": "translation"}}],
        })
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": 256}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 256}],
        "accessors": accessors,
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
        "nodes": [{"mesh": 0, "skin": 0}, {"name": "joint"}],
        "skins": [{"joints": [1]}],
        "animations": animations,
        "materials": [{}],
        "textures": [{}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    json_chunk = _pad(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = _pad(b"\x00" * 256, b"\x00")
    total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return (
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<I4s", len(json_chunk), b"JSON")
        + json_chunk
        + struct.pack("<I4s", len(bin_chunk), b"BIN\x00")
        + bin_chunk
    )
def write_glb(tmp_path, clips=None, bbox=None):
    """Write a GLB fixture to tmp_path."""
    path = tmp_path / "dragon.glb"
    path.write_bytes(build_glb_bytes(clips=clips, bbox=bbox))
    return path
def _pad(data, byte):
    """Pad GLB chunks to 4-byte alignment."""
    extra = (4 - (len(data) % 4)) % 4
    return data + byte * extra

### GLB validation
def test_parse_glb_round_trip(tmp_path):
    path = write_glb(tmp_path)
    gltf = parse_glb(str(path))
    assert gltf["asset"]["version"] == "2.0"
    assert len(gltf["animations"]) == len(config.REQUIRED_CLIPS)
def test_validate_passes_on_good_fixture(tmp_path):
    path = write_glb(tmp_path)
    ok, report = validate_dragon_glb(str(path))
    assert ok
    assert report["skin_count"] == 1
    assert report["bbox_height"] == 50
    assert report["total_triangles"] == 2
def test_validate_fails_when_clip_missing(tmp_path):
    path = write_glb(tmp_path, clips=config.REQUIRED_CLIPS[:-1])
    ok, report = validate_dragon_glb(str(path))
    assert not ok
    assert any("hatch" in p for p in report["problems"])
def test_validate_fails_when_bbox_too_small(tmp_path):
    path = write_glb(tmp_path, bbox={"min": [0, 0, 0], "max": [1, 10, 1]})
    ok, report = validate_dragon_glb(str(path))
    assert not ok
    assert any("Bounding-box height" in p for p in report["problems"])

### Meshy helpers / cache
def test_image_to_data_uri_png(tmp_path):
    image = tmp_path / "dragon.png"
    raw = b"\x89PNG\r\n\x1a\nfake"
    image.write_bytes(raw)
    uri = meshy.image_to_data_uri(str(image))
    assert uri.startswith("data:image/png;base64,")
    assert uri == "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
def test_generate_mesh_caches_without_second_create(tmp_path, monkeypatch):
    image = tmp_path / "dragon.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    fake = FakeRequests()
    monkeypatch.setattr(meshy, "requests", fake)
    first = meshy.generate_mesh(str(image), str(tmp_path / "out"), "dragon", api_key="key")
    assert fake.posts == 1
    assert first["cached"] is False
    assert os.path.exists(first["glb_path"])
    second = meshy.generate_mesh(str(image), str(tmp_path / "out"), "dragon", api_key="key")
    assert fake.posts == 1
    assert second["cached"] is True
    third = meshy.generate_mesh(str(image), str(tmp_path / "out"), "dragon", api_key="key", force=True)
    assert fake.posts == 2
    assert third["cached"] is False
def test_rodin_generate_mesh_happy_path_and_cache(tmp_path, monkeypatch):
    image = tmp_path / "dragon.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    fake = FakeRodinRequests()
    monkeypatch.setattr(rodin, "requests", fake)
    out_dir = tmp_path / "out"
    first = rodin.generate_mesh(str(image), str(out_dir), "dragon", prompt="green dragon")
    assert fake.create_posts == 1
    assert fake.status_posts == 1
    assert fake.download_posts == 1
    assert first["cached"] is False
    assert first["task_id"] == "rodin-task-1"
    assert os.path.exists(first["glb_path"])
    with open(first["glb_path"], "rb") as f:
        assert f.read() == b"rodin glb bytes"
    sidecar = json.loads((out_dir / "dragon.rodin-task.json").read_text())
    assert sidecar["task_uuid"] == "rodin-task-1"
    assert sidecar["subscription_key"] == "sub-1"
    assert sidecar["final_status"] == "Done"
    second = rodin.generate_mesh(str(image), str(out_dir), "dragon", prompt="green dragon")
    assert fake.create_posts == 1
    assert fake.status_posts == 1
    assert fake.download_posts == 1
    assert second["cached"] is True
def test_rodin_does_not_reuse_glb_for_unfinished_sidecar(tmp_path, monkeypatch):
    image = tmp_path / "dragon.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    fake = FakeRodinRequests()
    monkeypatch.setattr(rodin, "requests", fake)
    out_dir = tmp_path / "out"
    rodin.generate_mesh(str(image), str(out_dir), "dragon")
    sidecar_path = out_dir / "dragon.rodin-task.json"
    sidecar = json.loads(sidecar_path.read_text())
    sidecar["task_uuid"] = "rodin-task-resume"
    sidecar["subscription_key"] = "sub-resume"
    sidecar["final_status"] = None
    sidecar_path.write_text(json.dumps(sidecar))
    (out_dir / "dragon.glb").write_bytes(b"stale glb bytes")
    resumed = rodin.generate_mesh(str(image), str(out_dir), "dragon")
    assert resumed["cached"] is True
    assert resumed["task_id"] == "rodin-task-resume"
    assert fake.create_posts == 1
    assert fake.status_posts == 2
    assert fake.download_posts == 2
    assert (out_dir / "dragon.glb").read_bytes() == b"rodin glb bytes"
def test_rodin_failure_status_raises(tmp_path, monkeypatch):
    image = tmp_path / "dragon.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    fake = FakeRodinRequests(statuses=["Failed"])
    monkeypatch.setattr(rodin, "requests", fake)
    with pytest.raises(RuntimeError, match="failed"):
        rodin.generate_mesh(str(image), str(tmp_path / "out"), "dragon")
    assert fake.create_posts == 1
    assert fake.status_posts == 1
    assert fake.download_posts == 0
class FakeRequests:
    """Tiny requests stand-in for Meshy create/get/download flows."""
    def __init__(self):
        self.posts = 0
        self.gets = []
    def post(self, url, **kwargs):
        self.posts += 1
        return FakeResponse({"result": f"task-{self.posts}"})
    def get(self, url, **kwargs):
        self.gets.append(url)
        if "/image-to-3d/" in url:
            task_id = url.rsplit("/", 1)[-1]
            return FakeResponse({
                "id": task_id,
                "status": "SUCCEEDED",
                "progress": 100,
                "model_urls": {"glb": f"https://files.example/{task_id}.glb"},
                "thumbnail_url": f"https://files.example/{task_id}.png",
                "consumed_credits": 7,
            })
        if url.endswith(".glb"):
            return FakeResponse(content=b"glb bytes")
        return FakeResponse(content=b"png bytes")
class FakeResponse:
    """Tiny response object matching the methods meshy.py needs."""
    def __init__(self, body=None, content=b"", status_code=200):
        self.body = body
        self.content = content
        self.status_code = status_code
        self.text = json.dumps(body) if body is not None else content.decode("utf-8", "ignore")
    def json(self):
        return self.body
    def iter_content(self, chunk_size=65536):
        yield self.content
    def close(self):
        pass
class FakeRodinRequests:
    """Tiny requests stand-in for Rodin create/status/download flows."""
    def __init__(self, statuses=None):
        self.statuses = statuses or ["Done"]
        self.create_posts = 0
        self.status_posts = 0
        self.download_posts = 0
        self.gets = []
    def post(self, url, **kwargs):
        if url.endswith("/rodin"):
            self.create_posts += 1
            files = kwargs.get("files") or []
            assert [item[0] for item in files[:4]] == ["images", "tier", "mesh_mode", "texture_mode"]
            return FakeResponse({
                "uuid": f"rodin-task-{self.create_posts}",
                "jobs": {
                    "uuids": [f"job-{self.create_posts}"],
                    "subscription_key": f"sub-{self.create_posts}",
                },
            })
        if url.endswith("/status"):
            self.status_posts += 1
            return FakeResponse({"jobs": [{"status": status} for status in self.statuses]})
        if url.endswith("/download"):
            self.download_posts += 1
            return FakeResponse({
                "list": [
                    {"name": "preview.png", "url": "https://files.example/preview.png"},
                    {"name": "model.glb", "url": "https://files.example/rodin.glb"},
                ],
            })
        raise AssertionError(f"Unexpected Rodin POST {url}")
    def get(self, url, **kwargs):
        self.gets.append(url)
        if url.endswith(".glb"):
            return FakeResponse(content=b"rodin glb bytes")
        return FakeResponse(content=b"preview bytes")
def emit_fixture(path):
    """Emit a valid GLB fixture for manual CLI validation checks."""
    with open(path, "wb") as f:
        f.write(build_glb_bytes())
    return path
if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--emit":
        print(emit_fixture(sys.argv[2]))
    else:
        raise SystemExit("Usage: python tests/test_model3d.py --emit <path>")

# ===== END OF FILE tests/test_model3d.py =====
