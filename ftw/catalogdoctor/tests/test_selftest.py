from datetime import date
from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.compat import DateRecurringIndex
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid
from plone.app.folder.nogopip import GopipIndex
from Products.ExtendedPathIndex.ExtendedPathIndex import ExtendedPathIndex
from Products.PluginIndexes.BooleanIndex.BooleanIndex import BooleanIndex
from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
from Products.PluginIndexes.DateRangeIndex.DateRangeIndex import DateRangeIndex
from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
from Products.PluginIndexes.UUIDIndex.UUIDIndex import UUIDIndex
from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex


class TestSelftest(FunctionalTestCase):
    """Selftest for functional test case helpers."""

    maxDiff = None

    def setUp(self):
        super(TestSelftest, self).setUp()

        self.grant('Contributor')
        self.parent = create(Builder('folder')
                             .titled(u'parent'))
        self.child = create(Builder('folder')
                            .within(self.parent)
                            .titled(u'child'))

        # pretend we are something that supports recurring dates
        self.child.start = date(2010, 1, 1)
        self.child.recurrence = 'FREQ=DAILY;INTERVAL=1;COUNT=5'
        self.child.isPrincipiaFolderish = False
        self.reindex_object(self.child)

    def test_make_unhealthy_extra_rid_after_move(self):
        """Selftest that broken rids are created correctly.

        Apparently the problem surfaces only with plone < 5.

        Document in what way the catalog is broken when an extra rid is
        created. This has been verified against productive deployments
        where this issue is present.

        """
        self.make_unhealthy_extra_rid_after_move(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        extra_rid = result.get_unhealthy_rids()[0].rid

        self.assertTrue(extra_rid in self.catalog.paths)
        self.assertFalse(extra_rid in self.catalog.uids.values())

        uuid_index = self.catalog.indexes['UID']
        self.assertTrue(extra_rid in uuid_index._unindex)
        self.assertFalse(extra_rid in uuid_index._index.values())

        for name, index in self.catalog.indexes.items():
            # Purposefully don't use isinstance to avoid being bitten by
            # subclasses that change how the index behaves or add additional
            # internal data structures which we would not cover here, e.g.:
            # `ExtendedPathIndex` v.s. `PathIndex`.

            if index.__class__ in (FieldIndex, DateIndex,
                                   DateRecurringIndex, KeywordIndex):
                # These indices seem to consistently contain the extra rid, i.e.
                # it is left behind in the forward index and also in the
                # backward indices.
                rows_with_rid = find_keys_pointing_to_rid(
                    index._index, extra_rid)
                if rows_with_rid:
                    self.assertIn(extra_rid, index._unindex)
                if extra_rid in index._unindex:
                    self.assertGreaterEqual(len(rows_with_rid), 1)

            elif index.__class__ == ZCTextIndex:
                # Our broken object test provides values for all ZCTextIndex
                # indices. All ZCTextIndex indices that contain the extra rid
                # seem to contain it consistently.
                self.assertTrue(index.index.has_doc(extra_rid))

            elif index.__class__ == UUIDIndex:
                # We expect only one UUIDIndex and we have already handled it
                # explicitly above
                if name != 'UID':
                    self.fail('Unexpected uuid index: {}'.format(index))

            elif index.__class__ == DateRangeIndex:
                # The index seems to be consistent, forward and backward
                # indices contain the extra rid.
                self.assertTrue(extra_rid in index._unindex)
                self.assertTrue(any((
                    # _always: [rid]
                    extra_rid in index._always,
                    # all other extra indices provide: {date: [rid]}
                    find_keys_pointing_to_rid(index._since_only, extra_rid),
                    find_keys_pointing_to_rid(index._until_only, extra_rid),
                    find_keys_pointing_to_rid(index._since, extra_rid),
                    find_keys_pointing_to_rid(index._until, extra_rid),
                    )))

            elif index.__class__ == BooleanIndex:
                # The index seems to be consistent, forward and backward
                # indices contain the extra rid.
                self.assertIn(extra_rid, index._unindex)
                if index._unindex[extra_rid] == index._index_value:
                    self.assertIn(extra_rid, index._index)

            elif index.__class__ == ExtendedPathIndex:
                # The index seems to be consistent, forward and backward
                # indices contain the extra rid.
                # _unindex: {rid: path}
                self.assertIn(extra_rid, index._unindex)
                # _index_items: {path: rid}
                self.assertIn(extra_rid, index._index_items.values())
                # _index_parents: {path: [rid]} (path to rid of children)
                paths_with_rid_as_child = find_keys_pointing_to_rid(
                    index._index_parents, extra_rid)
                self.assertEqual(1, len(paths_with_rid_as_child))
                # _index: {component: {level: [rid]}} (component to level to rid)
                components_with_rid = [component for component, level_to_rid in index._index.items()
                                       if any(extra_rid in rids for level, rids in level_to_rid.items())]
                self.assertGreaterEqual(len(components_with_rid), 1)

            elif index.__class__ == GopipIndex:
                # This isn't a real index.
                pass

            else:
                self.fail('Unhandled index type: {}'.format(index))

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_uuid_unindex_not_in_catalog',
                'in_uuid_unindex_not_in_uuid_index',
                'uids_tuple_mismatches_paths_tuple',
            ),
            result.get_symptoms(extra_rid))

    def test_make_orphaned_rid(self):
        self.make_orphaned_rid(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        orphaned_rid = result.get_unhealthy_rids()[0].rid

        self.assertTrue(orphaned_rid in self.catalog.paths)
        self.assertFalse(orphaned_rid in self.catalog.uids.values())

        uuid_index = self.catalog.indexes['UID']
        self.assertTrue(orphaned_rid in uuid_index._unindex)
        self.assertFalse(orphaned_rid in uuid_index._index.values())

        for name, index in self.catalog.indexes.items():
            # Purposefully don't use isinstance to avoid being bitten by
            # subclasses that change how the index behaves or add additional
            # internal data structures which we would not cover here, e.g.:
            # `ExtendedPathIndex` v.s. `PathIndex`.

            if index.__class__ in (FieldIndex, DateIndex,
                                   DateRecurringIndex, KeywordIndex):
                # These indices seem to consistently contain the orphaned rid,
                # i.e. it is left behind in the forward index and also in the
                # backward indices.
                rows_with_rid = find_keys_pointing_to_rid(
                    index._index, orphaned_rid)
                if rows_with_rid:
                    self.assertIn(orphaned_rid, index._unindex)
                if orphaned_rid in index._unindex:
                    self.assertGreaterEqual(len(rows_with_rid), 1)

            elif index.__class__ == ZCTextIndex:
                # Our broken object test provides values for all ZCTextIndex
                # indices. All ZCTextIndex indices that contain the extra rid
                # seem to contain it consistently.
                self.assertTrue(index.index.has_doc(orphaned_rid))

            elif index.__class__ == UUIDIndex:
                # We expect only one UUIDIndex and we have already handled it
                # explicitly above
                if name != 'UID':
                    self.fail('Unexpected uuid index: {}'.format(index))

            elif index.__class__ == DateRangeIndex:
                # The index seems to be consistent, forward and backward
                # indices contain the orphaned rid.
                self.assertTrue(orphaned_rid in index._unindex)
                self.assertTrue(any((
                    # _always: [rid]
                    orphaned_rid in index._always,
                    # all other extra indices provide: {date: [rid]}
                    find_keys_pointing_to_rid(index._since_only, orphaned_rid),
                    find_keys_pointing_to_rid(index._until_only, orphaned_rid),
                    find_keys_pointing_to_rid(index._since, orphaned_rid),
                    find_keys_pointing_to_rid(index._until, orphaned_rid),
                    )))

            elif index.__class__ == BooleanIndex:
                # The index seems to be consistent, forward and backward
                # indices contain the orphaned rid.
                self.assertIn(orphaned_rid, index._unindex)
                if index._unindex[orphaned_rid] == index._index_value:
                    self.assertIn(orphaned_rid, index._index)

            elif index.__class__ == ExtendedPathIndex:
                # The index seems to be consistent, forward and backward
                # indices contain the orphaned rid.
                # _unindex: {rid: path}
                self.assertIn(orphaned_rid, index._unindex)
                # _index_items: {path: rid}
                self.assertIn(orphaned_rid, index._index_items.values())
                # _index_parents: {path: [rid]} (path to rid of children)
                paths_with_rid_as_child = find_keys_pointing_to_rid(
                    index._index_parents, orphaned_rid)
                self.assertEqual(1, len(paths_with_rid_as_child))
                # _index: {component: {level: [rid]}} (component to level to rid)
                components_with_rid = [component for component, level_to_rid in index._index.items()
                                       if any(orphaned_rid in rids for level, rids in level_to_rid.items())]
                self.assertGreaterEqual(len(components_with_rid), 1)

            elif index.__class__ == GopipIndex:
                # This isn't a real index.
                pass

            else:
                self.fail('Unhandled index type: {}'.format(index))

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_paths_values_not_in_uids_keys',
                'in_uuid_unindex_not_in_catalog',
                'in_uuid_unindex_not_in_uuid_index',
            ),
            result.get_symptoms(orphaned_rid))

    def test_make_missing_uuid_forward_index_entry(self):
        self.make_missing_uuid_forward_index_entry(self.parent)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        rid = result.get_unhealthy_rids()[0].rid

        self.assertTrue(rid in self.catalog.paths)
        self.assertTrue(rid in self.catalog.uids.values())

        uuid_index = self.catalog.indexes['UID']
        self.assertTrue(rid in uuid_index._unindex)
        self.assertFalse(rid in uuid_index._index.values())
        self.assertEqual(1, uuid_index._length())

        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_uuid_unindex_not_in_uuid_index',
            ),
            result.get_symptoms(rid))

    def test_drop_object_from_catalog_indexes(self):
        rid = self.get_rid(self.child)
        self.drop_object_from_catalog_indexes(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(rid, result.get_unhealthy_rids()[0].rid)
        self.assertTrue(rid in self.catalog.paths)
        self.assertTrue(rid in self.catalog.uids.values())

        uuid_index = self.catalog.indexes['UID']
        self.assertFalse(rid in uuid_index._unindex)
        self.assertFalse(rid in uuid_index._index.values())
        self.assertEqual(1, uuid_index._length())

        for index in self.catalog.indexes.values():
            self.assertFalse(index.getEntryForObject(rid))

        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_catalog_not_in_uuid_unindex',
            ),
            result.get_symptoms(rid))
