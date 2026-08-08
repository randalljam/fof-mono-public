# ===== START OF FILE apps/content_studio/model3d/validate_glb.py =====
# Pure-stdlib GLB inspector and dragon asset validator.

import os
import sys
import json
import struct
import argparse

from apps.content_studio.model3d import config

### GLB parsing
def parse_glb(path):
    """Parse a binary glTF 2.0 .glb file and return its JSON chunk.

    :param path: GLB path.
    :return: parsed glTF JSON dict.
    :raises ValueError: on malformed GLB structure.
    """
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 12:
        raise ValueError("GLB is shorter than the 12-byte header.")
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError("GLB magic must be 'glTF'.")
    if version != 2:
        raise ValueError(f"GLB version must be 2, got {version}.")
    if total_length != len(data):
        raise ValueError(f"GLB header length {total_length} does not match file length {len(data)}.")
    offset = 12
    json_chunk = None
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack_from("<I4s", data, offset)
        offset += 8
        chunk_end = offset + chunk_length
        if chunk_end > len(data):
            raise ValueError("GLB chunk length exceeds file length.")
        chunk = data[offset:chunk_end]
        offset = chunk_end
        if chunk_type == b"JSON":
            json_chunk = chunk
    if json_chunk is None:
        raise ValueError("GLB has no JSON chunk.")
    try:
        gltf = json.loads(json_chunk.rstrip(b" \x00").decode("utf-8"))
    except Exception as e:
        raise ValueError(f"GLB JSON chunk is malformed: {e}") from e
    if not isinstance(gltf, dict):
        raise ValueError("GLB JSON chunk must decode to an object.")
    return gltf
def summarize(gltf):
    """Summarize meshes, skins, animation durations, bbox, and materials.

    Node transforms are intentionally ignored for the scene bbox; this validator
    is a fast asset sanity check using POSITION accessor min/max values.

    :param gltf: parsed glTF JSON dict.
    :return: summary dict.
    """
    accessors = gltf.get("accessors") or []
    meshes = gltf.get("meshes") or []
    nodes = gltf.get("nodes") or []
    animations = _animation_summaries(gltf, accessors)
    bbox = _scene_bbox(gltf, accessors, meshes, nodes)
    return {
        "animation_names": [a["name"] for a in animations],
        "animations": animations,
        "skin_count": len(gltf.get("skins") or []),
        "joint_counts": [len(s.get("joints") or []) for s in gltf.get("skins") or []],
        "mesh_count": len(meshes),
        "total_triangles": _triangle_count(meshes, accessors),
        "node_count": len(nodes),
        "bbox": bbox,
        "bbox_height": _bbox_height(bbox),
        "material_count": len(gltf.get("materials") or []),
        "texture_count": len(gltf.get("textures") or []),
    }
def validate_dragon_glb(path, required_clips=None, min_height=20, max_height=100):
    """Validate the rigged dragon GLB contract used by the game pipeline.

    :param path: GLB path.
    :param required_clips: optional list of required animation clip names.
    :param min_height: minimum accepted bbox height in model units.
    :param max_height: maximum accepted bbox height in model units.
    :return: (ok, report) where report includes `problems`.
    """
    required_clips = required_clips or config.REQUIRED_CLIPS
    gltf = parse_glb(path)
    report = summarize(gltf)
    report["path"] = path
    problems = []
    names = {name.lower(): name for name in report["animation_names"]}
    for clip in required_clips:
        if clip.lower() not in names:
            problems.append(f"Missing required animation clip: {clip}")
    if report["skin_count"] < 1:
        problems.append("GLB must include at least one skin.")
    for anim in report["animations"]:
        if anim["duration"] <= 0.2:
            problems.append(f"Animation {anim['name']!r} duration must be > 0.2s.")
    height = report["bbox_height"]
    # The game divides model units by roughly 66 (scale 0.015), so the default
    # 20-100 GLB units lands near 0.3-1.5 scene units and catches accidental
    # tiny/huge rigs. Growth-stage builds (juvenile/adult) pass wider bounds.
    if height is None or height < min_height or height > max_height:
        problems.append(
            f"Bounding-box height must be between {min_height} and {max_height} model units.")
    report["problems"] = problems
    return (not problems, report)
def _animation_summaries(gltf, accessors):
    """Collect animation names and durations from sampler input accessors."""
    summaries = []
    for index, anim in enumerate(gltf.get("animations") or []):
        name = anim.get("name") or f"animation_{index}"
        duration = 0.0
        for sampler in anim.get("samplers") or []:
            accessor = _get(accessors, sampler.get("input"))
            max_values = accessor.get("max") if accessor else None
            if max_values:
                duration = max(duration, float(max_values[0]))
        summaries.append({"name": name, "duration": duration})
    return summaries
def _triangle_count(meshes, accessors):
    """Sum indexed triangle counts across mesh primitives."""
    total = 0
    for mesh in meshes:
        for primitive in mesh.get("primitives") or []:
            accessor = _get(accessors, primitive.get("indices"))
            if accessor:
                total += int(accessor.get("count", 0)) // 3
    return total
def _scene_bbox(gltf, accessors, meshes, nodes):
    """Compose POSITION accessor bounds for mesh-bearing nodes."""
    bbox = None
    mesh_indices = [node.get("mesh") for node in nodes if "mesh" in node]
    if not mesh_indices and meshes:
        mesh_indices = list(range(len(meshes)))
    for mesh_index in mesh_indices:
        mesh = _get(meshes, mesh_index)
        if not mesh:
            continue
        for primitive in mesh.get("primitives") or []:
            attrs = primitive.get("attributes") or {}
            accessor = _get(accessors, attrs.get("POSITION"))
            if accessor and accessor.get("min") and accessor.get("max"):
                bbox = _merge_bbox(bbox, accessor["min"], accessor["max"])
    return bbox
def _merge_bbox(bbox, min_values, max_values):
    """Merge one accessor min/max into an aggregate bbox."""
    if bbox is None:
        return {"min": list(min_values), "max": list(max_values)}
    return {
        "min": [min(bbox["min"][i], min_values[i]) for i in range(3)],
        "max": [max(bbox["max"][i], max_values[i]) for i in range(3)],
    }
def _bbox_height(bbox):
    """Return bbox Y extent."""
    if not bbox:
        return None
    return float(bbox["max"][1]) - float(bbox["min"][1])
def _get(seq, index):
    """Safely get a sequence item by int index."""
    if index is None:
        return None
    try:
        return seq[int(index)]
    except Exception:
        return None

### CLI
def main(argv=None):
    """Run the standalone GLB validator CLI."""
    p = argparse.ArgumentParser(description="Validate a rigged dragon GLB.")
    p.add_argument("glb", help="path to .glb file")
    args = p.parse_args(argv)
    ok, report = validate_dragon_glb(args.glb)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1
if __name__ == "__main__":
    sys.exit(main())

# ===== END OF FILE apps/content_studio/model3d/validate_glb.py =====
