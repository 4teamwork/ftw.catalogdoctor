from ftw.catalogdoctor.command import doctor_cmd
from ftw.catalogdoctor.healthcheck import CatalogHealthCheck
from ftw.catalogdoctor.testing import CATALOGDOCTOR_FUNCTIONAL
from ftw.testing import IS_PLONE_5
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from random import randint
from StringIO import StringIO
from unittest2 import TestCase
import transaction


class MockFormatter(object):

    def __init__(self):
        self.log = StringIO()

    def info(self, msg):
        self.log.write(msg + '\n')

    def warning(self, msg):
        self.log.write(msg + '\n')

    def error(self, msg):
        self.log.write(msg + '\n')

    def getlines(self):
        return self.log.getvalue().splitlines()


class Mock(object):
    pass


class FunctionalTestCase(TestCase):

    layer = CATALOGDOCTOR_FUNCTIONAL

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.portal_catalog = api.portal.get_tool('portal_catalog')
        self.catalog = self.portal_catalog._catalog
        self.catalog._v_nextid = 97

        self._chosen_rids = set()

    def run_command(self, *args):
        formatter = MockFormatter()
        command = ['-c'] + list(args)
        doctor_cmd(self.app, command, formatter=formatter)
        return formatter.getlines()

    def run_healthcheck(self):
        self.maybe_process_indexing_queue()  # enforce up to date catalog
        healthcheck = CatalogHealthCheck(self.portal_catalog)
        return healthcheck.run()

    def choose_next_rid(self):
        """Return a rid for testing currently unused.

        It will avoid returning rids already used by the catalog or already
        chosen by an earlier call to this method during the same test-case
        execution.

        Test-helper supposed to be called in a test-case once all objects
        have been added to the catalog by plone or your setup and you want to
        add specific rid entries to your catalog, usually in order to add
        superfluous entries to the catalog or its indices to setup your
        test-case.
        """
        index = getattr(self.catalog, '_v_nextid', 0)
        while (index in self.catalog.data
               or index in self.catalog.paths
               or index in self._chosen_rids):
            index = randint(-2000000000, 2000000000)

        self.catalog._v_nextid = index
        self._chosen_rids.add(index)
        return index

    def grant(self, *roles):
        setRoles(self.portal, TEST_USER_ID, list(roles))
        transaction.commit()

    def get_catalog_indexdata(self, obj):
        """Return the catalog index data for an object as dict.
        """
        self.maybe_process_indexing_queue()
        rid = self.portal_catalog.getrid('/'.join(obj.getPhysicalPath()))
        return self.portal_catalog.getIndexDataForRID(rid)

    def get_catalog_metadata(self, obj):
        """Return the catalog metadata for an object as dict.
        """
        self.maybe_process_indexing_queue()
        rid = self.portal_catalog.getrid('/'.join(obj.getPhysicalPath()))
        return self.portal_catalog.getMetadataForRID(rid)

    def reindex_object(self, obj):
        obj.reindexObject()
        self.maybe_process_indexing_queue()

    def maybe_process_indexing_queue(self):
        if not IS_PLONE_5:
            return

        from Products.CMFCore.indexing import processQueue
        processQueue()

    def get_rid(self, obj):
        path = self.get_physical_path(obj)
        return self.catalog.uids[path]

    def get_physical_path(self, obj):
        return '/'.join(obj.getPhysicalPath())
