# ===== START OF FILE apps/content_studio/frames.py =====
# Codec-agnostic frame math.
#
# Anything in here is pure Python (no PIL, no numpy) so it can be unit-tested
# without image libraries. The actual pixel handling lives in imaging.py.


### Sampling
def evenly_spaced_indices(total, count):
    """Pick `count` indices spread evenly across a sequence of `total` items.

    Always includes the first and last index when count >= 2, so the verifier
    sees the start and end of the motion. Returns sorted, de-duplicated indices.

    :param total: int, number of available items (e.g. animation frames).
    :param count: int, number of indices to pick.
    :return: list of ints in [0, total-1], ascending, length <= count.
    """
    if total <= 0:
        return []
    if count <= 0:
        return []
    if count >= total:
        return list(range(total))
    if count == 1:
        return [total // 2]
    # Spread across the full inclusive range [0, total-1].
    step = (total - 1) / (count - 1)
    picked = []
    for i in range(count):
        idx = int(round(i * step))
        if idx > total - 1:
            idx = total - 1
        if idx not in picked:
            picked.append(idx)
    return picked

### Labeling
def frame_label(position, total):
    """Build a short human label for a sampled frame.

    :param position: 1-based position of this frame within the sampled set.
    :param total: total number of sampled frames.
    :return: string like 'output frame 2 of 6'.
    """
    return f"output frame {position} of {total}"

# ===== END OF FILE apps/content_studio/frames.py =====
