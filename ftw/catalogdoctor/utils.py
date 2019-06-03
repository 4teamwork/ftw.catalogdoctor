def find_keys_pointing_to_rid(dictish, rid):
    """Return all entries in dictish item pointing to rid."""

    return [
        key for key, rids_for_key in dictish.items()
        if rid in rids_for_key
    ]
