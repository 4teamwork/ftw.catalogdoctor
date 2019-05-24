import pkg_resources


IS_PLONE_5 = pkg_resources.get_distribution('Products.CMFPlone').version >= '5'


if IS_PLONE_5:
    from Products.CMFCore.indexing import processQueue
else:
    # optional collective.indexing support
    try:
        from collective.indexing.queue import processQueue
    except ImportError:
        def processQueue():
            pass

# optional Products.DateRecurringIndex support
try:
    from Products.DateRecurringIndex.index import DateRecurringIndex
except ImportError:
    class DateRecurringIndex(object):
        pass
