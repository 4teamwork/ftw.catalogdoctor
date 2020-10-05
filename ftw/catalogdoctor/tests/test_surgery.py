from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.exceptions import CantPerformSurgery
from ftw.catalogdoctor.surgery import CatalogDoctor
from ftw.catalogdoctor.surgery import RemoveExtraRid
from ftw.catalogdoctor.surgery import RemoveOrphanedRid
from ftw.catalogdoctor.surgery import RemoveRidOrReindexObject
from ftw.catalogdoctor.tests import FunctionalTestCase
from plone.uuid.interfaces import IUUID


class TestSurgery(FunctionalTestCase):
    """Test various surgery can be performed successfully."""

    maxDiff = None

    def setUp(self):
        super(TestSurgery, self).setUp()

        self.grant('Contributor')
        self.parent = create(Builder('folder')
                             .titled(u'parent'))
        self.child = create(Builder('folder')
                            .within(self.parent)
                            .titled(u'child'))

    def test_surgery_remove_extra_rid_with_partial_uuid(self):
        self.make_unhealthy_extra_rid_after_move(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_uuid_unindex_not_in_catalog',
                'in_uuid_unindex_not_in_uuid_index',
                'uids_tuple_mismatches_paths_tuple',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveExtraRid, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_remove_extra_rid_without_partial_uuid(self):
        self.recatalog_object_with_new_rid(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'uids_tuple_mismatches_paths_tuple',
            ),
            unhealthy_rid.catalog_symptoms)

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveExtraRid, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_remove_extra_rid_with_stale_uuid(self):
        self.recatalog_object_with_new_rid(self.child, drop_from_indexes=False)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        unhealthy = result.get_unhealthy_rids()
        self.assertEqual(2, len(unhealthy))

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_uuid_index_not_in_catalog',
                'in_uuid_unindex_not_in_catalog',
                'uids_tuple_mismatches_paths_tuple',
            ),
            result.get_symptoms(unhealthy[0].rid))
        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_uuid_unindex_not_in_uuid_index',
            ),
            result.get_symptoms(unhealthy[1].rid))
        doctor = CatalogDoctor(self.catalog, unhealthy[0])
        self.assertIs(RemoveExtraRid, doctor.get_surgery())
        doctor = CatalogDoctor(self.catalog, unhealthy[1])
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())

        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_remove_extra_rid_with_stale_uuid_inverted_order(self):
        # make sure symptom order is inverted order as in
        # test_surgery_remove_extra_rid_with_stale_uuid
        self.recatalog_object_with_new_rid(
            self.child, drop_from_indexes=False, rid=-2000000000)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        unhealthy = result.get_unhealthy_rids()
        self.assertEqual(2, len(unhealthy))

        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_uuid_unindex_not_in_uuid_index',
            ),
            result.get_symptoms(unhealthy[0].rid))
        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_uuid_index_not_in_catalog',
                'in_uuid_unindex_not_in_catalog',
                'uids_tuple_mismatches_paths_tuple',
            ),
            result.get_symptoms(unhealthy[1].rid))

        doctor = CatalogDoctor(self.catalog, unhealthy[0])
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        doctor = CatalogDoctor(self.catalog, unhealthy[1])
        self.assertIs(RemoveExtraRid, doctor.get_surgery())

        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_remove_orphaned_rid_not_in_indexes(self):
        path = '/'.join(self.child.getPhysicalPath())
        self.drop_object_from_catalog_indexes(self.child)
        self.delete_object_silenty(self.child)
        del self.catalog.uids[path]

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_paths_values_not_in_uids_keys',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveOrphanedRid, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_remove_orphaned_rid_in_indexes(self):
        self.make_orphaned_rid(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_paths_values_not_in_uids_keys',
                'in_uuid_unindex_not_in_catalog',
                'in_uuid_unindex_not_in_uuid_index',
                ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveOrphanedRid, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_remove_orphaned_rid_where_object_still_present(self):
        rid = self.get_rid(self.child)
        del self.catalog.uids[self.get_physical_path(self.child)]
        uuid_index = self.catalog.indexes['UID']
        del uuid_index._index[uuid_index._unindex[rid]]
        uuid_index._length.change(-1)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]

        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_paths_values_not_in_uids_keys',
                'in_uuid_unindex_not_in_catalog',
                'in_uuid_unindex_not_in_uuid_index',
                ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveOrphanedRid, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

        self.assertDictContainsSubset(
            {'Creator': 'test_user_1_',
             'Description': [],
             'SearchableText': ['child', 'child'],
             'Subject': '',
             'Title': ['child'],
             'Type': u'Folder',
             'allowedRolesAndUsers': ['Anonymous'],
             'cmf_uid': '',
             'commentators': '',
             'effectiveRange': (-1560, None),
             'getId': 'child',
             'getObjPositionInParent': [],
             'getRawRelatedItems': '',
             'id': 'child',
             'in_reply_to': '',
             'is_default_page': 0,
             'is_folderish': 1,
             'meta_type': 'Dexterity Container',
             'path': '/plone/parent/child',
             'portal_type': 'Folder',
             'review_state': '',
             'sortable_title': 'child',
             'start': '',
             'sync_uid': '',
             'total_comments': 0},
            self.get_catalog_indexdata(self.child))

    def test_surgery_reindex_missing_uuid(self):
        self.make_missing_uuid_forward_index_entry(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]

        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_uuid_unindex_not_in_uuid_index',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_drop_duplicate_from_acquisition_from_catalog_for_missing_uuid(self):
        grandchild = create(Builder('folder')
                            .within(self.child)
                            .titled(u'nastygrandchild'))

        old_grandchild_path = '/'.join(grandchild.getPhysicalPath())
        # move object into parent's parent
        self.parent.manage_pasteObjects(
            self.child.manage_cutObjects(grandchild.getId()),
        )

        # re-register old grandchild path with different rid
        rid = self.choose_next_rid()
        self.catalog.uids[old_grandchild_path] = rid
        self.catalog.paths[rid] = old_grandchild_path
        self.catalog.indexes['UID']._unindex[rid] = IUUID(grandchild)
        self.catalog.data[rid] = {}
        self.catalog._length.change(1)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]

        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_uuid_unindex_not_in_uuid_index',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

        self.assertNotIn(old_grandchild_path, self.catalog.uids)
        self.assertNotIn(rid, self.catalog.paths)
        self.assertNotIn(rid, self.catalog.indexes['UID']._unindex)
        self.assertNotIn(rid, self.catalog.data)

    def test_surgery_remove_object_moved_into_parent_and_found_via_acquisition_abort(self):
        self.parent['qux'] = self.child
        broken_path = '/'.join(self.child.getPhysicalPath()[:-1] + ('qux',))

        rid = self.choose_next_rid()
        self.catalog.uids[broken_path] = rid
        self.catalog.paths[rid] = broken_path
        self.catalog.data[rid] = {}
        self.catalog._length.change(1)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]
        self.assertEqual(rid, unhealthy_rid.rid)
        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_catalog_not_in_uuid_unindex',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        with self.assertRaises(CantPerformSurgery):
            self.perform_surgeries(result)

    def test_surgery_remove_object_moved_into_parent_and_found_via_acquisition(self):
        grandchild = create(Builder('folder')
                            .within(self.child)
                            .titled(u'nastygrandchild'))

        old_grandchild_path = '/'.join(grandchild.getPhysicalPath())
        # move object into parent's parent
        self.parent.manage_pasteObjects(
            self.child.manage_cutObjects(grandchild.getId()),
        )

        # re-register old grandchild path with different rid
        rid = self.choose_next_rid()
        self.catalog.uids[old_grandchild_path] = rid
        self.catalog.paths[rid] = old_grandchild_path
        self.catalog.data[rid] = {}
        self.catalog._length.change(1)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]
        self.assertEqual(rid, unhealthy_rid.rid)
        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_catalog_not_in_uuid_unindex',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_remove_object_moved_with_parent_and_found_via_acquisition(self):
        level_1 = create(Builder('folder')
                         .within(self.child)
                        .titled(u'level 1'))
        level_2 = create(Builder('folder')
                        .within(level_1)
                        .titled(u'level 2'))

        old_level_2_path = '/'.join(level_2.getPhysicalPath())
        # move level_1 one level up, this also will move its child, level_2
        self.parent.manage_pasteObjects(
            self.child.manage_cutObjects(level_1.getId()),
        )

        # re-register level_2 path with different rid
        rid = self.choose_next_rid()
        self.catalog.uids[old_level_2_path] = rid
        self.catalog.paths[rid] = old_level_2_path
        self.catalog.data[rid] = {}
        self.catalog._length.change(1)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]
        self.assertEqual(rid, unhealthy_rid.rid)
        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_catalog_not_in_uuid_unindex',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

    def test_surgery_add_dropped_object_to_indices(self):
        self.drop_object_from_catalog_indexes(self.parent)
        self.assertEqual(
            {}, self.get_catalog_indexdata(self.parent, omit_empty=True))

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]
        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_catalog_not_in_uuid_unindex',
            ),
            result.get_symptoms(unhealthy_rid.rid))

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assert_no_unhealthy_rids()

        self.assertDictContainsSubset(
            {'Creator': 'test_user_1_',
             'Description': [],
             'SearchableText': ['parent', 'parent'],
             'Subject': '',
             'Title': ['parent'],
             'Type': u'Folder',
             'allowedRolesAndUsers': ['Anonymous'],
             'cmf_uid': '',
             'commentators': '',
             'effectiveRange': (-1560, None),
             'getId': 'parent',
             'getObjPositionInParent': [],
             'getRawRelatedItems': '',
             'id': 'parent',
             'in_reply_to': '',
             'is_default_page': 0,
             'is_folderish': 1,
             'meta_type': 'Dexterity Container',
             'path': '/plone/parent',
             'portal_type': 'Folder',
             'review_state': '',
             'sortable_title': 'parent',
             'start': '',
             'sync_uid': '',
             'total_comments': 0},
            self.get_catalog_indexdata(self.parent))

    def test_surgery_remove_untraversable_object_from_catalog(self):
        rid = self.get_rid(self.child)
        self.drop_object_from_catalog_indexes(self.child)
        self.delete_object_silenty(self.child)

        self.assertEqual(2, len(self.catalog))
        self.assertIn(rid, self.catalog.paths)
        self.assertIn(rid, self.catalog.data)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.get_unhealthy_rids()))
        unhealthy_rid = result.get_unhealthy_rids()[0]
        self.assertEqual(rid, unhealthy_rid.rid)
        self.assertEqual(
            (
                'in_catalog_not_in_uuid_index',
                'in_catalog_not_in_uuid_unindex',
            ),
            unhealthy_rid.catalog_symptoms)

        doctor = CatalogDoctor(self.catalog, unhealthy_rid)
        self.assertIs(RemoveRidOrReindexObject, doctor.get_surgery())
        self.perform_surgeries(result)

        self.assertEqual(1, len(self.catalog))
        self.assertNotIn(rid, self.catalog.paths)
        self.assertNotIn(rid, self.catalog.data)

        self.assert_no_unhealthy_rids()
