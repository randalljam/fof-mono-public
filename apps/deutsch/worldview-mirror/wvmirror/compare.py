"""Structured worldview comparison: the user's aggregated axis positions vs a
named atlas profile (the active "lens"), or any two atlas profiles.
This is the Mirror's core diff — a table, not vibes."""
from . import atlas as atlas_mod
from . import profile_store

ALIGNED_MAX = 0.7
LEANING_MAX = 1.5
def _alignment(delta):
    """Categorical label for an absolute position delta."""
    if delta is None:
        return "unknown"
    if delta < ALIGNED_MAX:
        return "aligned"
    if delta < LEANING_MAX:
        return "leaning-apart"
    return "divergent"
def compare_user_to_profile(user_profile, lens_profile, axes):
    """Per-axis rows comparing the user's aggregated positions to a lens profile.
    Rows are returned for every axis either side has a position on."""
    user_positions = profile_store.aggregate_positions(user_profile)
    lens_positions = atlas_mod.profile_positions_by_axis(lens_profile)
    rows = []
    for axis in axes:
        aid = axis["id"]
        user = user_positions.get(aid)
        lens = lens_positions.get(aid)
        if user is None and lens is None:
            continue
        delta = None
        if user is not None and lens is not None:
            delta = round(abs(user["position"] - lens["position"]), 2)
        rows.append({
            "axis": aid, "axis_label": axis["label"],
            "pole_neg": axis["pole_neg"]["label"], "pole_pos": axis["pole_pos"]["label"],
            "user_position": user["position"] if user else None,
            "user_basis": user["basis"] if user else None,
            "user_count": user["count"] if user else 0,
            "lens_position": lens["position"] if lens else None,
            "lens_summary": lens.get("summary") if lens else None,
            "delta": delta, "alignment": _alignment(delta),
        })
    order = {"divergent": 0, "leaning-apart": 1, "aligned": 2, "unknown": 3}
    rows.sort(key=lambda r: (order[r["alignment"]], -(r["delta"] or 0)))
    return rows
def compare_profiles(profile_a, profile_b, axes):
    """Per-axis rows comparing two atlas profiles (Atlas explorer view)."""
    pos_a = atlas_mod.profile_positions_by_axis(profile_a)
    pos_b = atlas_mod.profile_positions_by_axis(profile_b)
    rows = []
    for axis in axes:
        aid = axis["id"]
        a, b = pos_a.get(aid), pos_b.get(aid)
        if a is None and b is None:
            continue
        delta = round(abs(a["position"] - b["position"]), 2) if a and b else None
        rows.append({"axis": aid, "axis_label": axis["label"],
                     "pole_neg": axis["pole_neg"]["label"], "pole_pos": axis["pole_pos"]["label"],
                     "a_position": a["position"] if a else None, "b_position": b["position"] if b else None,
                     "a_summary": a.get("summary") if a else None, "b_summary": b.get("summary") if b else None,
                     "delta": delta, "alignment": _alignment(delta)})
    return rows
