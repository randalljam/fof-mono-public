# ===== START OF FILE apps/content_studio/model3d/cli.py =====
# Command-line entry point for the mesh -> Blender rigged GLB pipeline.

import os
import sys
import json
import argparse

from apps.content_studio.model3d import config, meshy, rodin, blender_runner, validate_glb

### Shared helpers
def _script_path(name):
    """Resolve a Blender script path relative to this module."""
    return os.path.join(os.path.dirname(__file__), "blender", name)
def _print_json(body):
    """Pretty-print a JSON-serializable body."""
    print(json.dumps(body, indent=2, sort_keys=True))
def _maybe_add_arg(args, flag, value):
    """Append a flag/value pair when value is present."""
    if value is not None:
        args.extend([flag, value])
def _mesh_provider_from_name(name):
    """Resolve a mesh provider module from a CLI provider name."""
    if name == "rodin":
        return rodin
    if name == "meshy":
        return meshy
    raise ValueError(f"Unknown mesh provider {name!r}.")
def _resolve_spec(args, out_dir):
    """Materialize a rig spec file when --height-units is given.

    :param args: parsed CLI args (may carry spec and height_units).
    :param out_dir: directory where a derived spec file may be written.
    :return: path to the spec file to pass to Blender, or None.
    """
    height = getattr(args, "height_units", None)
    if height is None:
        return args.spec
    spec = {}
    if args.spec:
        with open(args.spec) as fh:
            spec = json.load(fh)
    spec["height_units"] = height
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"rig-spec-h{int(height)}.json")
    with open(path, "w") as fh:
        json.dump(spec, fh, indent=2)
    return path
def _height_bounds(args):
    """Derive validation height bounds from --height-units when present."""
    height = getattr(args, "height_units", None)
    if height is None:
        return {}
    return {"min_height": height * 0.6, "max_height": height * 1.5}
def _mesh_options_from_args(args):
    """Translate CLI mesh flags into provider request options."""
    options = {}
    if getattr(args, "provider", config.DEFAULT_MESH_PROVIDER) == "rodin":
        if getattr(args, "prompt", None):
            options["prompt"] = args.prompt
        return options
    if getattr(args, "no_texture", False):
        options["should_texture"] = False
    if getattr(args, "polycount", None) is not None:
        options["target_polycount"] = args.polycount
    if getattr(args, "pose_mode", None) is not None:
        options["pose_mode"] = args.pose_mode
    if getattr(args, "texture_prompt", None):
        options["texture_prompt"] = args.texture_prompt
    return options

### Commands
def cmd_mesh(args):
    """Generate a GLB from an image."""
    provider = _mesh_provider_from_name(args.provider)
    result = provider.generate_mesh(
        args.image, args.out_dir, args.name, force=args.force,
        **_mesh_options_from_args(args),
    )
    _print_json(result)
    return 0
def cmd_rig(args):
    """Run the Blender dragon rig/export script."""
    script_args = ["--mesh", args.mesh, "--out", args.out]
    spec = _resolve_spec(args, os.path.dirname(os.path.abspath(args.out)))
    _maybe_add_arg(script_args, "--spec", spec)
    blender_runner.run_blender_script(_script_path("rig_dragon.py"), script_args=script_args)
    return 0
def cmd_preview(args):
    """Run the Blender preview-render script."""
    script_args = ["--glb", args.glb, "--out-dir", args.out_dir]
    _maybe_add_arg(script_args, "--clips", args.clips)
    if args.frames is not None:
        script_args.extend(["--frames", str(args.frames)])
    blender_runner.run_blender_script(_script_path("render_previews.py"), script_args=script_args)
    return 0
def cmd_validate(args):
    """Validate a rigged dragon GLB."""
    bounds = {}
    if args.min_height is not None:
        bounds["min_height"] = args.min_height
    if args.max_height is not None:
        bounds["max_height"] = args.max_height
    ok, report = validate_glb.validate_dragon_glb(args.glb, **bounds)
    _print_json(report)
    return 0 if ok else 1
def cmd_build(args):
    """Run mesh -> rig -> validate -> preview."""
    work_dir = args.work_dir or config.DEFAULT_WORK_DIR
    name = args.name or os.path.splitext(os.path.basename(args.image))[0]
    mesh_dir = os.path.join(work_dir, "meshes")
    preview_dir = os.path.join(work_dir, "previews")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    print("[model3d] step mesh", flush=True)
    provider = _mesh_provider_from_name(args.provider)
    mesh_result = provider.generate_mesh(
        args.image, mesh_dir, name, force=args.force,
        **_mesh_options_from_args(args),
    )
    print("[model3d] step rig", flush=True)
    rig_args = ["--mesh", mesh_result["glb_path"], "--out", args.out]
    _maybe_add_arg(rig_args, "--spec", _resolve_spec(args, work_dir))
    blender_runner.run_blender_script(_script_path("rig_dragon.py"), script_args=rig_args)
    print("[model3d] step validate", flush=True)
    ok, report = validate_glb.validate_dragon_glb(args.out, **_height_bounds(args))
    print("[model3d] step preview", flush=True)
    blender_runner.run_blender_script(
        _script_path("render_previews.py"),
        script_args=["--glb", args.out, "--out-dir", preview_dir],
    )
    summary = {
        "mesh_glb": mesh_result["glb_path"],
        "rigged_glb": args.out,
        "thumbnail": mesh_result["thumbnail_path"],
        "previews": preview_dir,
        "validation_ok": ok,
        "validation_problems": report.get("problems", []),
    }
    print("[model3d] summary")
    _print_json(summary)
    return 0 if ok else 1
def cmd_mcp_launch(args):
    """Launch Blender UI with the vendored MCP server enabled."""
    print(
        "[model3d] WARNING: the trusted-local MCP socket can execute arbitrary "
        "Python inside Blender.",
        flush=True,
    )
    pid = blender_runner.launch_blender_ui(_script_path("launch_with_mcp.py"))
    print(f"[model3d] launched Blender pid {pid}")
    print("[model3d] BlenderMCP server listens on localhost:9876")
    return 0

### Parser
def build_parser():
    """Build the model3d argparse parser."""
    p = argparse.ArgumentParser(
        prog="python -m apps.content_studio.model3d.cli",
        description="Build image -> generated mesh -> rigged/animated GLB assets.",
    )
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("mesh", help="generate a GLB from an image")
    m.add_argument("--image", required=True, help="input PNG/JPEG")
    m.add_argument("--out-dir", required=True, help="output directory")
    m.add_argument("--name", required=True, help="output file stem")
    m.add_argument("--provider", choices=("rodin", "meshy"), default=config.DEFAULT_MESH_PROVIDER, help="mesh provider")
    m.add_argument("--force", action="store_true", help="ignore cache and create a new mesh task")
    m.add_argument("--no-texture", action="store_true", help="disable Meshy texturing")
    m.add_argument("--polycount", type=int, default=None, help="target polygon count")
    m.add_argument("--pose-mode", default=None, help="pose mode: a-pose, t-pose, or empty string")
    m.add_argument("--texture-prompt", default=None, help="optional texture prompt")
    m.add_argument("--prompt", default=None, help="optional Rodin prompt")
    m.set_defaults(func=cmd_mesh)
    r = sub.add_parser("rig", help="rig/animate a Meshy GLB via Blender")
    r.add_argument("--mesh", required=True, help="input mesh GLB")
    r.add_argument("--out", required=True, help="output rigged GLB")
    r.add_argument("--spec", default=None, help="optional rig spec JSON")
    r.add_argument("--height-units", type=float, default=None, help="target GLB height in model units (default 45)")
    r.set_defaults(func=cmd_rig)
    pr = sub.add_parser("preview", help="render preview frames via Blender")
    pr.add_argument("--glb", required=True, help="input rigged GLB")
    pr.add_argument("--out-dir", required=True, help="preview output directory")
    pr.add_argument("--clips", default=None, help="comma-separated clip names")
    pr.add_argument("--frames", type=int, default=None, help="frames per clip")
    pr.set_defaults(func=cmd_preview)
    v = sub.add_parser("validate", help="validate a rigged dragon GLB")
    v.add_argument("--glb", required=True, help="input rigged GLB")
    v.add_argument("--min-height", type=float, default=None, help="min bbox height in model units")
    v.add_argument("--max-height", type=float, default=None, help="max bbox height in model units")
    v.set_defaults(func=cmd_validate)
    b = sub.add_parser("build", help="mesh -> rig -> validate -> preview")
    b.add_argument("--image", required=True, help="input PNG/JPEG")
    b.add_argument("--out", required=True, help="output rigged GLB")
    b.add_argument("--work-dir", default=None, help="working directory")
    b.add_argument("--name", default=None, help="asset name/stem")
    b.add_argument("--spec", default=None, help="optional rig spec JSON")
    b.add_argument("--provider", choices=("rodin", "meshy"), default=config.DEFAULT_MESH_PROVIDER, help="mesh provider")
    b.add_argument("--prompt", default=None, help="optional Rodin prompt")
    b.add_argument("--force", action="store_true", help="ignore mesh cache")
    b.add_argument("--height-units", type=float, default=None, help="target GLB height in model units (default 45)")
    b.set_defaults(func=cmd_build)
    ml = sub.add_parser(
        "mcp-launch",
        help="launch Blender UI with trusted-local code-executing MCP socket",
    )
    ml.set_defaults(func=cmd_mcp_launch)
    return p
def main(argv=None):
    """Run the model3d CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
if __name__ == "__main__":
    sys.exit(main())

# ===== END OF FILE apps/content_studio/model3d/cli.py =====
