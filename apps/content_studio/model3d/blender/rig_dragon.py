# ===== START OF FILE apps/content_studio/model3d/blender/rig_dragon.py =====
# Rig + animate a Meshy-generated dragon mesh and export a game-ready GLB.
#
# Runs INSIDE Blender (headless):
#   blender --background --factory-startup --python-exit-code 1 \
#       --python rig_dragon.py -- --mesh in.glb --out dragon.glb [--spec spec.json]
#
# Pipeline: import GLB -> normalize (scale/ground/center) -> heuristic armature
# from mesh landmarks -> automatic-weight skinning -> author the eight game
# clips as Actions pushed to NLA tracks -> export GLB (NLA tracks become the
# glTF animation clips, named exactly after the tracks).
#
# Game contract (apps/math-quiz/dragon/world/dragon.js):
#   - clips matched case-insensitively: idle walk fly wing-stretch play jump fire hatch
#   - model loaded at scale 0.015; ~45 Blender/glTF units tall reads ~0.7 in scene
#   - forward is glTF +Z, i.e. Blender -Y; clips animate in place (game moves root)

import bpy
import json
import math
import sys
from mathutils import Vector

### Spec defaults (overridable via --spec JSON)
DEFAULT_SPEC = {
    "height_units": 45.0,   # bbox Z extent after normalize (0.015 game scale -> ~0.68)
    "fps": 24,
    "clips": {
        "idle":         {"seconds": 2.0},
        "walk":         {"seconds": 1.0},
        "fly":          {"seconds": 1.0},
        "wing-stretch": {"seconds": 2.0},
        "play":         {"seconds": 1.5},
        "jump":         {"seconds": 1.2},
        "fire":         {"seconds": 1.5},
        "hatch":        {"seconds": 2.5},
    },
}

### CLI plumbing
def parse_args():
    """Parse the script args that follow the '--' separator in Blender's argv."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {"mesh": None, "out": None, "spec": None}
    i = 0
    while i < len(argv):
        key = argv[i].lstrip("-")
        if key in args and i + 1 < len(argv):
            args[key] = argv[i + 1]
            i += 2
        else:
            i += 1
    if not args["mesh"] or not args["out"]:
        raise SystemExit("usage: rig_dragon.py -- --mesh in.glb --out out.glb [--spec spec.json]")
    return args
def load_spec(path):
    """Merge a user spec JSON over DEFAULT_SPEC (shallow for scalars, per-clip deep)."""
    spec = json.loads(json.dumps(DEFAULT_SPEC))
    if path:
        with open(path) as fh:
            user = json.load(fh)
        for key, value in user.items():
            if key == "clips":
                for clip, overrides in value.items():
                    spec["clips"].setdefault(clip, {}).update(overrides)
            else:
                spec[key] = value
    return spec

### Scene setup and mesh normalization
def clear_scene():
    """Remove every object factory startup ships with (cube, camera, light)."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
def import_mesh(path):
    """Import the GLB and return a single joined mesh object."""
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"no mesh objects found in {path}")
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active
    # Drop any empties/armatures the source file carried; we build our own rig.
    for obj in list(bpy.context.scene.objects):
        if obj is not mesh:
            bpy.data.objects.remove(obj, do_unlink=True)
    mesh.name = "Dragon"
    return mesh
def normalize_mesh(mesh, height_units):
    """Scale to the target height, center on X/Y, and rest feet on Z=0."""
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    coords = [v.co for v in mesh.data.vertices]
    lo = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
    hi = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
    height = hi.z - lo.z
    if height <= 0:
        raise RuntimeError("degenerate mesh: zero height")
    factor = height_units / height
    mesh.scale = (factor, factor, factor)
    bpy.ops.object.transform_apply(scale=True)
    coords = [v.co for v in mesh.data.vertices]
    lo = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
    hi = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
    offset = Vector((-(lo.x + hi.x) / 2.0, -(lo.y + hi.y) / 2.0, -lo.z))
    for v in mesh.data.vertices:
        v.co += offset
    mesh.data.update()
    return bbox_of(mesh)
def bbox_of(mesh):
    """Return (lo, hi) corner Vectors of the mesh's local-space bounding box."""
    coords = [v.co for v in mesh.data.vertices]
    lo = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
    hi = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
    return lo, hi

### Landmark detection
def landmarks_from_mesh(mesh):
    """Estimate rig landmarks by sampling vertex clusters.

    Blender space here: +Z up, dragon faces -Y (glTF +Z forward), tail toward +Y.
    Heuristics are tuned for a chibi/baby creature: oversized head on top-front,
    wings as the widest geometry in the upper half, tail as the rearmost cluster.
    :param mesh: normalized mesh object.
    :return: dict of named Vector positions used to place bones.
    """
    verts = [v.co.copy() for v in mesh.data.vertices]
    lo, hi = bbox_of(mesh)
    size = hi - lo
    def centroid(sel):
        """Average position of a vertex subset (falls back to bbox center)."""
        if not sel:
            return (lo + hi) / 2.0
        total = Vector((0, 0, 0))
        for c in sel:
            total += c
        return total / len(sel)
    head_verts = [c for c in verts if c.z > lo.z + size.z * 0.62]
    head = centroid(head_verts)
    snout_verts = [c for c in head_verts if c.y < head.y - size.y * 0.08]
    snout = centroid(snout_verts) if snout_verts else Vector((head.x, head.y - size.y * 0.2, head.z - size.z * 0.05))
    belly_band = [c for c in verts if lo.z + size.z * 0.25 < c.z < lo.z + size.z * 0.55]
    belly = centroid(belly_band)
    hips = Vector((0, belly.y + size.y * 0.12, lo.z + size.z * 0.30))
    chest = Vector((0, belly.y - size.y * 0.05, lo.z + size.z * 0.48))
    tail_verts = [c for c in verts if c.y > lo.y + size.y * 0.80]
    tail_tip = centroid([c for c in tail_verts if c.y > lo.y + size.y * 0.92]) if tail_verts else Vector((0, hi.y, lo.z + size.z * 0.1))
    upper_half = [c for c in verts if c.z > lo.z + size.z * 0.35]
    wing_l_verts = [c for c in upper_half if c.x > lo.x + size.x * 0.72]
    wing_r_verts = [c for c in upper_half if c.x < lo.x + size.x * 0.28]
    wing_l_tip = centroid([c for c in wing_l_verts if c.x > lo.x + size.x * 0.88]) if wing_l_verts else Vector((hi.x, chest.y + size.y * 0.1, chest.z + size.z * 0.1))
    wing_r_tip = centroid([c for c in wing_r_verts if c.x < lo.x + size.x * 0.12]) if wing_r_verts else Vector((lo.x, chest.y + size.y * 0.1, chest.z + size.z * 0.1))
    wing_root_z = chest.z + size.z * 0.08
    marks = {
        "hips": hips,
        "chest": chest,
        "neck": Vector((0, chest.y - size.y * 0.02, lo.z + size.z * 0.58)),
        "head": Vector((0, head.y, head.z)),
        "head_top": Vector((0, head.y, min(head.z + size.z * 0.18, hi.z))),
        "snout": snout,
        "tail_tip": Vector((tail_tip.x * 0.2, tail_tip.y, tail_tip.z)),
        "wing_l_root": Vector((size.x * 0.10, chest.y + size.y * 0.06, wing_root_z)),
        "wing_r_root": Vector((-size.x * 0.10, chest.y + size.y * 0.06, wing_root_z)),
        "wing_l_tip": wing_l_tip,
        "wing_r_tip": wing_r_tip,
        "foot_l": Vector((size.x * 0.18, hips.y + size.y * 0.02, lo.z)),
        "foot_r": Vector((-size.x * 0.18, hips.y + size.y * 0.02, lo.z)),
        "hand_l": Vector((size.x * 0.22, chest.y - size.y * 0.10, chest.z - size.z * 0.06)),
        "hand_r": Vector((-size.x * 0.22, chest.y - size.y * 0.10, chest.z - size.z * 0.06)),
        "size": size,
        "lo": lo,
        "hi": hi,
    }
    print("[rig] landmarks:")
    for key, value in marks.items():
        print(f"[rig]   {key}: {tuple(round(v, 2) for v in value)}" if isinstance(value, Vector) else f"[rig]   {key}: {value}")
    return marks

### Armature construction
def build_armature(marks):
    """Create the dragon armature from landmarks and return the armature object."""
    arm_data = bpy.data.armatures.new("DragonRig")
    arm_obj = bpy.data.objects.new("DragonRig", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    size = marks["size"]
    def add(name, head, tail, parent=None, connect=False):
        """Create one edit bone."""
        bone = eb.new(name)
        bone.head = head
        bone.tail = tail
        bone.roll = 0.0
        if parent:
            bone.parent = eb[parent]
            bone.use_connect = connect
        return bone
    hips, chest = marks["hips"], marks["chest"]
    add("root", Vector((0, 0, 0)), Vector((0, size.y * 0.25, 0)))
    add("body", hips, chest, parent="root")
    add("chest", chest, marks["neck"], parent="body", connect=True)
    add("neck", marks["neck"], marks["head"], parent="chest", connect=True)
    add("head", marks["head"], marks["head_top"], parent="neck", connect=True)
    jaw_tip = Vector((0, marks["snout"].y, marks["snout"].z - size.z * 0.06))
    add("jaw", marks["head"], jaw_tip, parent="head")
    tail_a = hips + (marks["tail_tip"] - hips) * 0.4
    tail_b = hips + (marks["tail_tip"] - hips) * 0.75
    add("tail.1", Vector((0, hips.y + size.y * 0.05, hips.z)), tail_a, parent="body")
    add("tail.2", tail_a, tail_b, parent="tail.1", connect=True)
    add("tail.3", tail_b, marks["tail_tip"], parent="tail.2", connect=True)
    for side, sign in (("L", 1), ("R", -1)):
        wing_root = marks[f"wing_{side.lower()}_root"]
        wing_tip = marks[f"wing_{side.lower()}_tip"]
        wing_mid = wing_root + (wing_tip - wing_root) * 0.5
        add(f"wing.1.{side}", wing_root, wing_mid, parent="chest")
        add(f"wing.2.{side}", wing_mid, wing_tip, parent=f"wing.1.{side}", connect=True)
        hand = marks[f"hand_{side.lower()}"]
        shoulder = Vector((sign * size.x * 0.10, chest.y - size.y * 0.04, chest.z))
        add(f"arm.{side}", shoulder, hand, parent="chest")
        foot = marks[f"foot_{side.lower()}"]
        hip = Vector((sign * size.x * 0.12, hips.y, hips.z))
        knee = hip + (foot - hip) * 0.5 + Vector((0, -size.y * 0.04, 0))
        add(f"thigh.{side}", hip, knee, parent="body")
        add(f"shin.{side}", knee, foot, parent=f"thigh.{side}", connect=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    print(f"[rig] armature bones: {len(arm_data.bones)}")
    return arm_obj
def skin_mesh(mesh, arm_obj):
    """Bind the mesh to the armature, preferring automatic weights.

    Bone-heat can fail on non-manifold meshes while parent_set still reports
    success, silently producing an unskinned export. Verify real weight
    coverage and fall back to deterministic distance-based weights if needed.
    """
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    mesh.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    except RuntimeError as exc:
        print(f"[rig] automatic weights raised: {exc}")
    coverage = weight_coverage(mesh)
    if coverage >= 0.95:
        print(f"[rig] skinning: automatic weights OK (coverage {coverage:.0%})")
        return
    print(f"[rig] skinning: bone heat coverage only {coverage:.0%}; using distance-based fallback")
    manual_skin(mesh, arm_obj)
def weight_coverage(mesh):
    """Fraction of vertices holding at least one nonzero vertex-group weight."""
    if not mesh.vertex_groups:
        return 0.0
    weighted = sum(1 for v in mesh.data.vertices if any(g.weight > 0.0 for g in v.groups))
    return weighted / max(1, len(mesh.data.vertices))
def manual_skin(mesh, arm_obj):
    """Assign smooth nearest-bone weights by distance to bone segments."""
    for vg in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(vg)
    segments = []
    for bone in arm_obj.data.bones:
        if bone.name == "root":
            continue
        segments.append((bone.name, bone.head_local.copy(), bone.tail_local.copy()))
    groups = {name: mesh.vertex_groups.new(name=name) for name, _, _ in segments}
    def seg_distance(point, head, tail):
        """Distance from a point to the bone's head-tail segment."""
        axis = tail - head
        length_sq = axis.length_squared
        if length_sq == 0:
            return (point - head).length
        t = max(0.0, min(1.0, (point - head).dot(axis) / length_sq))
        return (point - (head + axis * t)).length
    for v in mesh.data.vertices:
        dists = sorted((seg_distance(v.co, h, t), name) for name, h, t in segments)
        nearest = dists[:3]
        raw = [(name, 1.0 / max(d, 0.05) ** 2) for d, name in nearest]
        total = sum(w for _, w in raw)
        for name, w in raw:
            groups[name].add([v.index], w / total, "REPLACE")
    modifier = mesh.modifiers.new("Armature", "ARMATURE")
    modifier.object = arm_obj
    mesh.parent = arm_obj
    print(f"[rig] skinning: distance-based weights on {len(mesh.data.vertices)} vertices")

### Animation authoring
class ClipWriter:
    """Small helper to keyframe pose bones for one Action."""
    def __init__(self, arm_obj, name, seconds, fps):
        self.arm = arm_obj
        self.fps = fps
        self.frames = max(2, int(round(seconds * fps)))
        self.action = bpy.data.actions.new(name)
        arm_obj.animation_data.action = self.action
        for pb in arm_obj.pose.bones:
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
    def key(self, bone, t, rot=None, loc=None, scale=None):
        """Insert keyframes for a bone at normalized time t (0..1)."""
        frame = 1 + t * (self.frames - 1)
        pb = self.arm.pose.bones[bone]
        if rot is not None:
            pb.rotation_euler = rot
            pb.keyframe_insert("rotation_euler", frame=frame)
        if loc is not None:
            pb.location = loc
            pb.keyframe_insert("location", frame=frame)
        if scale is not None:
            pb.scale = scale
            pb.keyframe_insert("scale", frame=frame)
    def wave(self, bone, channel, axis, amplitude, cycles=1.0, phase=0.0, offset=0.0, samples=8):
        """Keyframe a sine wave on one channel component across the clip."""
        for i in range(samples + 1):
            t = i / samples
            value = offset + amplitude * math.sin(2 * math.pi * (cycles * t + phase))
            frame = 1 + t * (self.frames - 1)
            pb = self.arm.pose.bones[bone]
            if channel == "rot":
                vec = list(pb.rotation_euler)
                vec[axis] = value
                pb.rotation_euler = vec
                pb.keyframe_insert("rotation_euler", frame=frame)
            elif channel == "loc":
                vec = list(pb.location)
                vec[axis] = value
                pb.location = vec
                pb.keyframe_insert("location", frame=frame)
            elif channel == "scale":
                pb.scale = (1 + value, 1 + value, 1 + value)
                pb.keyframe_insert("scale", frame=frame)
    def finish(self):
        """Push the action onto its own NLA track (glTF exports tracks as clips)."""
        for fc in self.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
        track = self.arm.animation_data.nla_tracks.new()
        track.name = self.action.name
        track.strips.new(self.action.name, 1, self.action)
        self.arm.animation_data.action = None
        print(f"[rig] clip '{self.action.name}': {self.frames} frames")
def author_clips(arm_obj, spec, marks):
    """Author all eight game clips. Amplitudes are radians / Blender units."""
    fps = spec["fps"]
    size = marks["size"]
    hop = size.z * 0.05
    arm_obj.animation_data_create()

    def clip(name):
        return ClipWriter(arm_obj, name, spec["clips"][name]["seconds"], fps)
    # idle — soft breathing, blink-scale on head, lazy tail sway, tiny wing rise
    w = clip("idle")
    w.wave("body", "scale", 0, 0.025, cycles=1)
    w.wave("head", "rot", 0, 0.05, cycles=1, phase=0.25)
    w.wave("tail.2", "rot", 2, 0.12, cycles=1)
    w.wave("tail.3", "rot", 2, 0.18, cycles=1, phase=0.15)
    w.wave("wing.1.L", "rot", 1, 0.06, cycles=1)
    w.wave("wing.1.R", "rot", 1, -0.06, cycles=1)
    w.finish()
    # walk — in-place bouncy waddle: alternating legs, counter arm swing, head bob
    w = clip("walk")
    w.wave("thigh.L", "rot", 0, 0.35, cycles=1)
    w.wave("thigh.R", "rot", 0, -0.35, cycles=1)
    w.wave("shin.L", "rot", 0, 0.20, cycles=1, phase=0.25)
    w.wave("shin.R", "rot", 0, -0.20, cycles=1, phase=0.25)
    w.wave("arm.L", "rot", 0, -0.25, cycles=1)
    w.wave("arm.R", "rot", 0, 0.25, cycles=1)
    w.wave("body", "loc", 2, hop * 0.5, cycles=2, offset=hop * 0.25)
    w.wave("body", "rot", 2, 0.06, cycles=1)
    w.wave("head", "rot", 0, 0.08, cycles=2)
    w.wave("tail.2", "rot", 2, 0.15, cycles=1)
    w.finish()
    # fly — strong wing flaps, gentle hover bob, legs tucked
    w = clip("fly")
    w.wave("wing.1.L", "rot", 1, 0.65, cycles=1)
    w.wave("wing.1.R", "rot", 1, -0.65, cycles=1)
    w.wave("wing.2.L", "rot", 1, 0.35, cycles=1, phase=0.12)
    w.wave("wing.2.R", "rot", 1, -0.35, cycles=1, phase=0.12)
    w.wave("body", "loc", 2, hop, cycles=1, phase=0.25)
    for bone, angle in (("thigh.L", 0.5), ("thigh.R", 0.5), ("shin.L", 0.6), ("shin.R", 0.6)):
        w.key(bone, 0.0, rot=(angle, 0, 0))
        w.key(bone, 1.0, rot=(angle, 0, 0))
    w.wave("tail.2", "rot", 0, 0.10, cycles=1)
    w.finish()
    # wing-stretch — slow proud spread, hold, settle back
    w = clip("wing-stretch")
    for side, sign in (("L", 1), ("R", -1)):
        w.key(f"wing.1.{side}", 0.0, rot=(0, 0, 0))
        w.key(f"wing.1.{side}", 0.35, rot=(0, sign * 0.85, 0))
        w.key(f"wing.1.{side}", 0.65, rot=(0, sign * 0.85, 0))
        w.key(f"wing.1.{side}", 1.0, rot=(0, 0, 0))
        w.key(f"wing.2.{side}", 0.0, rot=(0, 0, 0))
        w.key(f"wing.2.{side}", 0.35, rot=(0, sign * 0.45, 0))
        w.key(f"wing.2.{side}", 0.65, rot=(0, sign * 0.45, 0))
        w.key(f"wing.2.{side}", 1.0, rot=(0, 0, 0))
    w.key("chest", 0.0, rot=(0, 0, 0))
    w.key("chest", 0.5, rot=(-0.12, 0, 0))
    w.key("chest", 1.0, rot=(0, 0, 0))
    w.key("head", 0.0, rot=(0, 0, 0))
    w.key("head", 0.5, rot=(-0.15, 0, 0))
    w.key("head", 1.0, rot=(0, 0, 0))
    w.finish()
    # play — happy bounces with head tilts and fast tail wags
    w = clip("play")
    w.wave("body", "loc", 2, hop * 1.6, cycles=2, offset=hop * 0.8)
    w.wave("body", "rot", 1, 0.10, cycles=2)
    w.wave("head", "rot", 2, 0.25, cycles=2, phase=0.25)
    w.wave("tail.2", "rot", 2, 0.35, cycles=3)
    w.wave("tail.3", "rot", 2, 0.45, cycles=3, phase=0.1)
    w.wave("wing.1.L", "rot", 1, 0.25, cycles=2)
    w.wave("wing.1.R", "rot", 1, -0.25, cycles=2)
    w.finish()
    # jump — anticipation crouch, spring up, tuck, land with a squash
    w = clip("jump")
    w.key("body", 0.0, loc=(0, 0, 0), scale=(1, 1, 1))
    w.key("body", 0.2, loc=(0, 0, -hop), scale=(1.05, 1.05, 0.9))
    w.key("body", 0.5, loc=(0, 0, size.z * 0.35), scale=(0.97, 0.97, 1.06))
    w.key("body", 0.8, loc=(0, 0, 0), scale=(1.04, 1.04, 0.93))
    w.key("body", 1.0, loc=(0, 0, 0), scale=(1, 1, 1))
    for side in ("L", "R"):
        w.key(f"thigh.{side}", 0.0, rot=(0, 0, 0))
        w.key(f"thigh.{side}", 0.2, rot=(0.5, 0, 0))
        w.key(f"thigh.{side}", 0.5, rot=(0.7, 0, 0))
        w.key(f"thigh.{side}", 1.0, rot=(0, 0, 0))
    w.key("wing.1.L", 0.5, rot=(0, 0.5, 0))
    w.key("wing.1.R", 0.5, rot=(0, -0.5, 0))
    w.key("wing.1.L", 1.0, rot=(0, 0, 0))
    w.key("wing.1.R", 1.0, rot=(0, 0, 0))
    w.finish()
    # fire — rear back, thrust head forward with open jaw, chest puff
    w = clip("fire")
    w.key("chest", 0.0, rot=(0, 0, 0), scale=(1, 1, 1))
    w.key("chest", 0.25, rot=(0.18, 0, 0), scale=(1.06, 1.06, 1.06))
    w.key("chest", 0.45, rot=(-0.10, 0, 0))
    w.key("chest", 1.0, rot=(0, 0, 0), scale=(1, 1, 1))
    w.key("head", 0.0, rot=(0, 0, 0))
    w.key("head", 0.25, rot=(0.30, 0, 0))
    w.key("head", 0.45, rot=(-0.35, 0, 0))
    w.key("head", 0.75, rot=(-0.30, 0, 0))
    w.key("head", 1.0, rot=(0, 0, 0))
    w.key("jaw", 0.0, rot=(0, 0, 0))
    w.key("jaw", 0.4, rot=(0.45, 0, 0))
    w.key("jaw", 0.75, rot=(0.40, 0, 0))
    w.key("jaw", 1.0, rot=(0, 0, 0))
    w.wave("tail.3", "rot", 2, 0.08, cycles=2)
    w.finish()
    # hatch — start curled tiny, pop up, wobble, curious look around
    w = clip("hatch")
    w.key("body", 0.0, loc=(0, 0, -size.z * 0.18), scale=(0.65, 0.65, 0.55))
    w.key("body", 0.35, loc=(0, 0, hop), scale=(1.08, 1.08, 1.1))
    w.key("body", 0.5, loc=(0, 0, 0), scale=(0.97, 0.97, 0.95))
    w.key("body", 0.65, loc=(0, 0, 0), scale=(1, 1, 1))
    w.key("body", 1.0, loc=(0, 0, 0), scale=(1, 1, 1))
    w.key("head", 0.0, rot=(0.6, 0, 0))
    w.key("head", 0.4, rot=(-0.15, 0, 0))
    w.key("head", 0.6, rot=(0, 0, 0.3))
    w.key("head", 0.8, rot=(0, 0, -0.3))
    w.key("head", 1.0, rot=(0, 0, 0))
    for side, sign in (("L", 1), ("R", -1)):
        w.key(f"wing.1.{side}", 0.0, rot=(0, sign * -0.3, 0))
        w.key(f"wing.1.{side}", 0.5, rot=(0, sign * 0.4, 0))
        w.key(f"wing.1.{side}", 0.75, rot=(0, 0, 0))
        w.key(f"wing.1.{side}", 1.0, rot=(0, 0, 0))
    w.wave("tail.2", "rot", 2, 0.2, cycles=2, phase=0.5)
    w.finish()

### Export
def export_glb(out_path, fps):
    """Export the scene to GLB with NLA tracks as named animation clips."""
    bpy.context.scene.render.fps = fps
    kwargs = {
        "filepath": out_path,
        "export_format": "GLB",
        "export_animations": True,
        "export_animation_mode": "NLA_TRACKS",
        "export_skins": True,
        "export_yup": True,
        "export_apply": False,
    }
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError:
        # Older exporter signatures: drop the newer kwargs and retry.
        kwargs.pop("export_animation_mode", None)
        bpy.ops.export_scene.gltf(**kwargs)
    print(f"[rig] exported {out_path}")

### Main
def main():
    args = parse_args()
    spec = load_spec(args["spec"])
    clear_scene()
    mesh = import_mesh(args["mesh"])
    normalize_mesh(mesh, spec["height_units"])
    marks = landmarks_from_mesh(mesh)
    arm_obj = build_armature(marks)
    skin_mesh(mesh, arm_obj)
    author_clips(arm_obj, spec, marks)
    export_glb(args["out"], spec["fps"])
    print("[rig] done")
main()
# ===== END OF FILE apps/content_studio/model3d/blender/rig_dragon.py =====
