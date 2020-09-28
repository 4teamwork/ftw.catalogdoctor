def find_keys_pointing_to_rid(dictish, rid):
    """Return all entries in dictish item pointing to rid.

    The values in dictish can be either the rid as a single value or a
    collection containing the rid.

    """
    return [
        key for key, rids_or_rid in dictish.items()
        if contains_or_equals_rid(rid, rids_or_rid)
    ]


def contains_or_equals_rid(rid, rids_or_rid):
    """Return whether rids_or_rid contains or equals a rid."""

    try:
        return rid in rids_or_rid
    except TypeError:
        return rid == rids_or_rid


def is_shorter_path_to_same_file(shorter, longer):
    """Return whether `shorter` is a part of `longer`.

    Will return `True` when `shorter` is a path pointing to the same last
    segment but shortened by some intermediate segments that are present in
    `longer`.
    """
    shorter_path_segments = shorter.rstrip('/').strip('/').split('/')
    longer_segments = longer.rstrip('/').strip('/').split('/')
    if len(shorter_path_segments) >= len(longer_segments):
        return False

    # last element must be the same.
    if shorter_path_segments.pop() != longer_segments.pop():
        return False

    # every segment in longer must be present in shorter in correct order.
    for segment in longer_segments:
        if shorter_path_segments and shorter_path_segments[0] == segment:
            shorter_path_segments.pop(0)
    return len(shorter_path_segments) == 0
