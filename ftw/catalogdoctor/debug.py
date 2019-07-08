from pprint import pprint


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
