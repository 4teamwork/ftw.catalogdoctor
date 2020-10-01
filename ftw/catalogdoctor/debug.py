from ftw.catalogdoctor.utils import find_keys_pointing_to_rid
from plone import api
from plone.app.folder.nogopip import GopipIndex
from pprint import pprint
from Products.ExtendedPathIndex.ExtendedPathIndex import ExtendedPathIndex
from Products.PluginIndexes.BooleanIndex.BooleanIndex import BooleanIndex
from Products.PluginIndexes.common.UnIndex import UnIndex
from Products.PluginIndexes.DateRangeIndex.DateRangeIndex import DateRangeIndex
from Products.PluginIndexes.PathIndex.PathIndex import PathIndex
from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex


_marker = object()
_no_entry = '<NO ENTRY>'


def btrees_to_python_collections(maybe_btrees):
    """Convert collections from btrees to python collections for debugging.

    WARNING: naive implementation:
    - converts sets to lists
    - should not be used on large data structures
    - should only be used to debug

    Only use it to display things on the command line. Better not
    programmatically work with the result otherwise. Stick to BTrees if you
    can.

    This method is intended to help displaying catalog data structures on the
    command line for debugging. It can be uses in combination with pprint to
    quickly analize the state of the catalog's internal data structures.

    """
    if isinstance(maybe_btrees, (int, basestring)):
        return maybe_btrees
    elif hasattr(maybe_btrees, 'items'):
        return dict((key, btrees_to_python_collections(val))
                     for key, val in maybe_btrees.items())
    else:
        return list(maybe_btrees)


def pprint_btrees(btrees):
    """pretty print a collection from btrees.

    Sample output looks like:

    >>> index = plone.portal_catalog._catalog.indexes['path']
    >>> pprint_btrees(index._index)
    {None: {1: [97], 2: [98, 99]},
     'child': {2: [98]},
     'otherchild': {2: [99]},
     'parent': {1: [97, 98, 99]},
     'plone': {0: [97, 98, 99]}}

    >>> pprint_btrees(index._unindex)
    {97: '/plone/parent',
     98: '/plone/parent/child',
     99: '/plone/parent/otherchild'}

    >>> pprint_btrees(index._index_items)
    {'/plone/parent': 97,
     '/plone/parent/child': 98,
     '/plone/parent/otherchild': 99}

    >>> pprint_btrees(index._index_parents)
    {'/plone': [97],
     '/plone/parent': [98, 99]}

    """
    pprint(btrees_to_python_collections(btrees))


def pprint_obj_catalog_data(obj, idxs=None, metadata=False):
    """Pretty-print data in catalog for a content object obj.

    WARNING: naive implementation:
    - potentially loads the full catalog into memory
    - should only be used to debug

    """
    obj_path = '/'.join(obj.getPhysicalPath())
    pprint(get_catalog_data(uid=obj_path, idxs=idxs, metadata=metadata))


def pprint_path_catalog_data(path, idxs=None, metadata=False):
    """Pretty-print data in catalog for a content object obj.

    WARNING: naive implementation:
    - potentially loads the full catalog into memory
    - should only be used to debug

    """
    pprint(get_catalog_data(uid=path, idxs=idxs, metadata=metadata))


def pprint_rid_catalog_data(rid, idxs=None, metadata=False):
    """Pretty-print data in catalog for rid.

    WARNING: naive implementation:
    - potentially loads the full catalog into memory
    - should only be used to debug

    """
    pprint(get_catalog_data(rid=rid, idxs=idxs, metadata=metadata))


def get_catalog_data(rid=None, uid=None, idxs=None, metadata=False):
    """Return all data in catalog for rid or uid."""

    if rid and uid:
        raise TypeError('Either specify rid or uid, both are unsupported.')

    portal_catalog = api.portal.get_tool('portal_catalog')
    zcatalog = portal_catalog._catalog

    data = {}
    if rid:
        uid = zcatalog.paths.get(rid, _no_entry)
    elif uid:
        rid = zcatalog.uids.get(uid, _no_entry)
        # early abort when we lookup the rid but can't find it
        if rid == _no_entry:
            data['uids (path->rid)'] = {uid: rid}
            return data

    data['indexes'] = get_extended_indexes_data(zcatalog, rid, idxs=idxs)
    if metadata:
        data['metadata'] = portal_catalog.getMetadataForRID(rid)

    # get data in uids/paths and make sure to display what is actually stored
    # in there, not the argument we are passed in by re-fetching the
    # information from the data structures.
    uid_in_paths = zcatalog.paths.get(rid, _no_entry)  # placeholder when empty
    paths_data = {rid: uid_in_paths}
    # also get potential duplicates
    for key, value in zcatalog.paths.items():
        if value == uid and key != rid:
            paths_data[key] = value
    data['paths (rid->path)'] = paths_data

    rid_in_uids = zcatalog.uids.get(uid, _no_entry)  # placeholder when empty
    uids_data = {uid: rid_in_uids}
    # also get potential duplicates
    for key, value in zcatalog.uids.items():
        if value == rid and key != uid:
            uids_data[key] = value
    data['uids (path->rid)'] = uids_data

    return data


def get_extended_indexes_data(zcatalog, rid, idxs=None):
    """Return all data stored in all or selected zcatalog indexes for rid."""
    if idxs is not None:
        idxs = set(idxs)

    indexes_data = {}
    for index_name in zcatalog.indexes:
        if idxs is not None and index_name not in idxs:
            continue
        index = zcatalog.getIndex(index_name)
        indexes_data[index_name] = get_extended_index_data(index, rid)
    return indexes_data


def get_extended_index_data(index, rid):
    """Return all data stored in an index for rid.

    This usually includes backward and forward indexes and also helper indexes
    if available.
    """
    if isinstance(index, GopipIndex):
        return '<UNSUPPORTED>'

    index_data = {}

    if isinstance(index, PathIndex):
        index_data['unindex'] = {}
        unindex_value = index._unindex.get(rid, _marker)
        if unindex_value is not _marker:
            index_data['unindex'][rid] = unindex_value

        index_data['index'] = {}
        for component, level_to_rid in index._index.items():
            for level, rids in level_to_rid.items():
                if rid in rids:
                    index_data['index'][(component, level,)] = rid

        if isinstance(index, ExtendedPathIndex):
            index_data['index_items'] = {}
            index_values = find_keys_pointing_to_rid(index._index_items, rid)
            for index_value in index_values:
                index_data['index_items'][index_value] = rid

            index_data['index_parents'] = {}
            index_values = find_keys_pointing_to_rid(index._index_parents, rid)
            for index_value in index_values:
                index_data['index_parents'][index_value] = rid

    elif isinstance(index, ZCTextIndex):
        # just show what word ids are available for the rid to indicate it
        # is present in the index. not bothering to look up the acual
        # string represented by the term. may be omitted if not useful.
        index_data['docwords'] = {}
        if index.index.has_doc(rid):
            index_data['docwords'][rid] = index.index.get_words(rid)

    elif isinstance(index, DateRangeIndex):
        index_data['always'] = []
        if rid in index._always:
            index_data['always'] = [rid]

        index_data['since_only'] = {}
        index_values = find_keys_pointing_to_rid(index._since_only, rid)
        for index_value in index_values:
            index_data['since_only'][index_value] = rid

        index_data['until_only'] = {}
        index_values = find_keys_pointing_to_rid(index._until_only, rid)
        for index_value in index_values:
            index_data['until_only'][index_value] = rid

        index_data['since'] = {}
        index_values = find_keys_pointing_to_rid(index._since, rid)
        for index_value in index_values:
            index_data['since'][index_value] = rid

        index_data['until'] = {}
        index_values = find_keys_pointing_to_rid(index._until, rid)
        for index_value in index_values:
            index_data['until'][index_value] = rid

        index_data['unindex'] = {}
        unindex_value = index._unindex.get(rid, _marker)
        if unindex_value is not _marker:
            index_data['unindex'][rid] = unindex_value

    elif isinstance(index, BooleanIndex):
        # _index is special an only contains either `True` or `False`
        # values, we are just interested in _unindex
        index_data['unindex'] = {}
        unindex_value = index._unindex.get(rid, _marker)
        if unindex_value is not _marker:
            index_data['unindex'][rid] = unindex_value

    elif isinstance(index, UnIndex):
        index_data['unindex'] = {}
        unindex_value = index._unindex.get(rid, _marker)
        if unindex_value is not _marker:
            index_data['unindex'][rid] = unindex_value

        index_data['index'] = {}
        index_values = find_keys_pointing_to_rid(index._index, rid)
        for index_value in index_values:
            index_data['index'][index_value] = rid

    return index_data
