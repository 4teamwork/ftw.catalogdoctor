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
