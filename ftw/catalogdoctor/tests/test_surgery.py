from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.exceptions import CantPerformSurgery
from ftw.catalogdoctor.surgery import CatalogDoctor
from ftw.catalogdoctor.surgery import ReindexMissingUUID
from ftw.catalogdoctor.surgery import RemoveExtraRid
from ftw.catalogdoctor.surgery import RemoveOrphanedRid
from ftw.catalogdoctor.surgery import RemoveRidOrReindexObject
from ftw.catalogdoctor.tests import FunctionalTestCase


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
        doctor.perform_surgery()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

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
        doctor.perform_surgery()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

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
        doctor.perform_surgery()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

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
        doctor.perform_surgery()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

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
        self.assertIs(ReindexMissingUUID, doctor.get_surgery())
        doctor.perform_surgery()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

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
            doctor.perform_surgery()

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
        doctor.perform_surgery()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

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
        doctor.perform_surgery()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

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
        doctor.perform_surgery()

        self.assertEqual(1, len(self.catalog))
        self.assertNotIn(rid, self.catalog.paths)
        self.assertNotIn(rid, self.catalog.data)

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())
