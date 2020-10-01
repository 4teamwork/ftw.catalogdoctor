from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent
from ftw.catalogdoctor.command import doctor_cmd
from ftw.catalogdoctor.compat import processQueue
from ftw.catalogdoctor.healthcheck import CatalogHealthCheck
from ftw.catalogdoctor.scheduler import SurgeryScheduler
from ftw.catalogdoctor.testing import CATALOGDOCTOR_FUNCTIONAL
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from random import randint
from StringIO import StringIO
from unittest import TestCase
import transaction
import uuid


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

    def perform_surgeries(self, healthcheck_result):
        scheduler = SurgeryScheduler(
            healthcheck_result, catalog=self.portal_catalog)
        return scheduler.perform_surgeries()

    def assert_no_unhealthy_rids(self):
        result = self.run_healthcheck()
        formatter = MockFormatter()
        result.write_result(formatter)
        msg = '\n'.join(
            ['Expected healthy catalog but found:'] + formatter.getlines()
        )
        self.assertTrue(result.is_healthy(), msg=msg)

    def choose_next_rid(self):
        """Return a currently unused rid for testing.

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

    def get_catalog_indexdata(self, obj, omit_empty=False):
        """Return the catalog index data for an object as dict.
        """
        self.maybe_process_indexing_queue()
        index_data = self.portal_catalog.getIndexDataForRID(self.get_rid(obj))
        if omit_empty:
            index_data = dict((key, value) for key, value in index_data.items()
                              if value)
        return index_data

    def get_catalog_metadata(self, obj):
        """Return the catalog metadata for an object as dict.
        """
        self.maybe_process_indexing_queue()
        return self.portal_catalog.getMetadataForRID(self.get_rid(obj))

    def reindex_object(self, obj):
        obj.reindexObject()
        self.maybe_process_indexing_queue()

    def maybe_process_indexing_queue(self):
        processQueue()

    def get_rid(self, obj):
        path = self.get_physical_path(obj)
        return self.catalog.uids[path]

    def get_physical_path(self, obj):
        return '/'.join(obj.getPhysicalPath())

    def make_unhealthy_extra_rid_after_move(self, obj, new_id=None):
        """Make catalog unhealthy and create an extra rid for obj.

        :param obj: the object that will have an unhealthy additional rid
        :param new_id: the target object id after the object has been moved.
          An UUID4 is used if this argument is not supplied.

        Simulate an issue when objects are reindexed prematurely while plone is
        processing the IObjectWillBeMovedEvent and IObjectMovedEvent events.
        This issue only surfaces when `ftw.copymovepatches` is installed and
        is also described in detail in:
        https://github.com/4teamwork/opengever.core/pull/5533
        The premature reindex can be caused by e.g. a catalog query in another
        event handler for IOBjectMoved.

        - Move the object without firing moved events. Disconnects object from
          catalogs path->rid mapping as the object will have a new path.
        - Reindex the object, this adds a new entry to the catalog and the
          catalog indices. As already mentioned the catalog uses its internal
          path->rid mapping to decide if the object is inserted or updated.
        - Simulate ftw.copymovepatches optimized move that is applied to the
          old data which breaks the catalog.

        """
        new_id = new_id or str(uuid.uuid4())
        old_rid = self.get_rid(obj)  # keep old rid for ftw.copymovepatches

        # move without firing events, disconnect ob from catalog
        old_id = self.child.getId()
        ob = self.parent._getOb(old_id)
        self.parent._delObject(old_id, suppress_events=True)
        ob = aq_base(ob)
        ob._setId(new_id)
        self.parent._setObject(new_id, ob, set_owner=0, suppress_events=True)
        ob = self.parent._getOb(new_id)
        ob._postCopy(self, op=1)

        # reindex ob, create new rid in catalog and new entries
        self.reindex_object(ob)

        # simulate ftw.copymovepatches optimized move, breaks catalog entries
        new_path = '/'.join(ob.getPhysicalPath())
        old_path = self.catalog.paths[old_rid]
        del self.catalog.uids[old_path]
        self.catalog.uids[new_path] = old_rid
        self.catalog.paths[old_rid] = new_path

        return ob

    def make_orphaned_rid(self, obj):
        """Make catalog unhealthy and create an orphaned rid for obj.

        :param obj: the object that will be deleted and leave an unhealthy rid
                    behind.

        This simulates an issue that surfaces when an object with an extra
        rid as created by `make_unhealthy_extra_rid_after_move` is deleted.

        """
        ob = self.make_unhealthy_extra_rid_after_move(obj)
        self.delete_object(ob)

        self.maybe_process_indexing_queue()
        return ob

    def recatalog_object_with_new_rid(self, obj, drop_from_indexes=True, rid=None):
        """Make catalog unhealthy by recataloging an object with a new rid.

        This will leave the old rid behind in catalog metadata and in the
        rid->path mapping but remove it from all indexes.

        """
        if drop_from_indexes:
            self.drop_object_from_catalog_indexes(obj)

        path = '/'.join(obj.getPhysicalPath())
        del self.catalog.uids[path]
        if rid:
            # prepare insert with the specified rid, make sure catalog length
            # is correct in that case
            assert rid not in self.catalog.paths
            self.catalog.uids[path] = rid
            self.catalog.paths[rid] = path
            self.catalog._length.change(1)

        self.catalog.catalogObject(obj, path)

    def delete_object(self, obj):
        aq_parent(aq_inner(obj)).manage_delObjects([obj.getId()])

    def delete_object_silenty(self, obj):
        """Silently delete the object without firing any reindexing events."""

        parent = aq_parent(aq_inner(obj))
        parent._delObject(obj.getId(), suppress_events=True)

    def make_missing_uuid_forward_index_entry(self, obj):
        """Make catalog unhealthy by dropping an item from the forward index.


        :param obj: the object for which the UUIDIndex will be set into an
                    inconsistent state.

        """
        rid = self.get_rid(obj)

        uuid_index = self.catalog.indexes['UID']
        uuid = uuid_index._unindex[rid]
        del uuid_index._index[uuid]
        uuid_index._length.change(-1)

        return obj

    def drop_object_from_catalog_indexes(self, obj):
        """Make catalog unhealthy by dropping `obj` from all indexes."""

        self.drop_rid_from_catalog_indexes(self.get_rid(obj))

    def drop_rid_from_catalog_indexes(self, rid):
        """Make catalog unhealthy by dropping `rid` from all indexes."""

        for index in self.catalog.indexes.values():
            index.unindex_object(rid)
