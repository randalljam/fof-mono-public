# ===== START OF FILE apps/content_studio/model3d/blender/render_previews.py =====
# Render still-frame previews of a rigged GLB so an AI (or human) can visually
# verify the rig and clips without opening Blender.
#
# Runs INSIDE Blender (headless):
#   blender --background --factory-startup --python-exit-code 1 \
#       --python render_previews.py -- --glb dragon.glb --out-dir previews \
#       [--clips idle,walk] [--frames 4]
#
# Output: <out-dir>/rest_<angle>.png (4 turntable angles of the rest pose) and
# <out-dir>/<clip>_f<i>.png (N frames sampled evenly across each clip).

import bpy
import math
import os
import sys
from mathutils import Vector

### CLI plumbing
def parse_args():
    """Parse script args after the '--' separator."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {"glb": None, "out-dir": None, "clips": None, "frames": "4"}
    i = 0
    while i < len(argv):
        key = argv[i].lstrip("-")
        if key in args and i + 1 < len(argv):
            args[key] = argv[i + 1]
            i += 2
        else:
            i += 1
    if not args["glb"] or not args["out-dir"]:
        raise SystemExit("usage: render_previews.py -- --glb x.glb --out-dir dir [--clips csv] [--frames n]")
    return args

### Scene setup
def clear_scene():
    """Remove factory-startup default objects."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
def import_glb(path):
    """Import the GLB; return (all objects, armature or None, world bbox lo/hi)."""
    bpy.ops.import_scene.gltf(filepath=path)
    objs = list(bpy.context.scene.objects)
    armature = next((o for o in objs if o.type == "ARMATURE"), None)
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in objs:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            lo = Vector((min(lo.x, world.x), min(lo.y, world.y), min(lo.z, world.z)))
            hi = Vector((max(hi.x, world.x), max(hi.y, world.y), max(hi.z, world.z)))
    return objs, armature, (lo, hi)
def setup_render(out_dir):
    """Pick a render engine that works headless on this machine, set output."""
    scene = bpy.context.scene
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.image_settings.file_format = "PNG"
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    print(f"[preview] engine: {scene.render.engine}")
    if scene.render.engine == "BLENDER_WORKBENCH":
        shading = scene.display.shading
        shading.color_type = "TEXTURE"
        shading.light = "STUDIO"
    world = bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.9, 0.9, 0.92, 1.0)
        bg.inputs[1].default_value = 1.0
    bpy.context.scene.world = world
    os.makedirs(out_dir, exist_ok=True)
def add_camera_and_light(bbox, azimuth_deg):
    """Place a camera on a turntable orbit framing the bbox; add a sun light."""
    lo, hi = bbox
    center = (lo + hi) / 2.0
    extent = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
    distance = extent * 2.4
    az = math.radians(azimuth_deg)
    elev = math.radians(18)
    cam_pos = center + Vector((
        distance * math.cos(elev) * math.sin(az),
        -distance * math.cos(elev) * math.cos(az),
        distance * math.sin(elev),
    ))
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = cam_pos
    direction = center - cam_pos
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    if not any(o.type == "LIGHT" for o in bpy.context.scene.objects):
        sun_data = bpy.data.lights.new("Sun", type="SUN")
        sun_data.energy = 3.0
        sun = bpy.data.objects.new("Sun", sun_data)
        bpy.context.scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(50), 0, math.radians(30))
        fill_data = bpy.data.lights.new("Fill", type="SUN")
        fill_data.energy = 1.2
        fill = bpy.data.objects.new("Fill", fill_data)
        bpy.context.scene.collection.objects.link(fill)
        fill.rotation_euler = (math.radians(60), 0, math.radians(210))
    return cam
def render_to(path):
    """Render one still to the given path."""
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[preview] wrote {path}")

### Clip playback
def solo_clip(armature, clip_name):
    """Assign the named action to the armature; return clip frame length."""
    action = next((a for a in bpy.data.actions if a.name.lower() == clip_name.lower()), None)
    if action is None or armature is None:
        return None
    if armature.animation_data is None:
        armature.animation_data_create()
    for track in armature.animation_data.nla_tracks:
        track.mute = True
    armature.animation_data.action = action
    return action.frame_range

### Main
def main():
    args = parse_args()
    out_dir = args["out-dir"]
    clear_scene()
    objs, armature, bbox = import_glb(args["glb"])
    setup_render(out_dir)
    cam = add_camera_and_light(bbox, 30)
    # Rest pose turntable: 4 angles.
    if armature and armature.animation_data:
        armature.animation_data.action = None
        for track in armature.animation_data.nla_tracks:
            track.mute = True
    for angle in (0, 90, 180, 270):
        bpy.data.objects.remove(cam, do_unlink=True)
        cam = add_camera_and_light(bbox, angle + 30)
        render_to(os.path.join(out_dir, f"rest_{angle}.png"))
    # Clip frames.
    clip_names = [c for c in (args["clips"] or "").split(",") if c] or \
        sorted({a.name for a in bpy.data.actions})
    frames = max(2, int(args["frames"]))
    for clip in clip_names:
        frame_range = solo_clip(armature, clip)
        if frame_range is None:
            print(f"[preview] clip not found: {clip}")
            continue
        start, end = frame_range
        for i in range(frames):
            t = i / (frames - 1)
            bpy.context.scene.frame_set(int(round(start + t * (end - start))))
            render_to(os.path.join(out_dir, f"{clip}_f{i}.png"))
    print("[preview] done")
main()
# ===== END OF FILE apps/content_studio/model3d/blender/render_previews.py =====
