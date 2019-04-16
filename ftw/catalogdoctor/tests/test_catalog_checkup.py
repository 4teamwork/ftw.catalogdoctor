from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.catalog import CatalogCheckup
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.tests import get_physical_path


class TestCatalogCheckup(FunctionalTestCase):

    def setUp(self):
        super(TestCatalogCheckup, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))

    def run_checkup(self):
        checkup = CatalogCheckup(self.portal_catalog)
        checkup.run()
        return checkup

    def test_initial_catalog_is_healthy(self):
        checkup = self.run_checkup()

        self.assertTrue(checkup.is_healthy())
        self.assertTrue(checkup.is_length_healthy())

    def test_aberrations_make_catalog_unhealthy(self):
        checkup = self.run_checkup()
        self.assertTrue(checkup.is_healthy())

        checkup.report_aberration(self.choose_next_rid())
        self.assertFalse(checkup.is_healthy())

    def test_longer_uids_make_catalog_unhealthy(self):
        checkup = self.run_checkup()
        self.assertTrue(checkup.is_length_healthy())

        checkup.catalog.uids['foo'] = self.choose_next_rid()

        self.assertFalse(checkup.is_length_healthy())

    def test_longer_paths_make_catalog_unhealthy(self):
        checkup = self.run_checkup()
        self.assertTrue(checkup.is_length_healthy())

        checkup.catalog.paths[self.choose_next_rid()] = 'foo'

        self.assertFalse(checkup.is_length_healthy())

    def test_longer_metadata_make_catalog_unhealthy(self):
        checkup = self.run_checkup()
        self.assertTrue(checkup.is_length_healthy())

        checkup.catalog.data[self.choose_next_rid()] = dict()

        self.assertFalse(checkup.is_length_healthy())

    def test_detects_duplicate_entry_in_rid_to_path_mapping_keys(self):
        broken_rid = self.choose_next_rid()
        self.catalog.paths[broken_rid] = get_physical_path(self.folder)
        self.catalog._length.change(1)

        checkup = self.run_checkup()

        self.assertFalse(checkup.is_healthy())
        self.assertEqual(1, len(checkup.aberrations))
        self.assertEqual(
            {
                'uids_tuple_mismatches_paths_tuple',
                'in_paths_keys_not_in_metadata_keys',
                'in_paths_keys_not_in_uids_values',
            },
            checkup.get_symptoms(broken_rid))

    def test_detects_missing_entry_in_rid_to_path_mapping_values(self):
        path = get_physical_path(self.folder)
        rid = self.catalog.uids.pop(path)

        checkup = self.run_checkup()

        self.assertFalse(checkup.is_healthy())
        self.assertEqual(1, len(checkup.aberrations))
        self.assertEqual(
            {
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_paths_values_not_in_uids_keys',
            },
            checkup.get_symptoms(rid))

    def test_detects_duplicate_entry_in_path_to_rid_mapping(self):
        path = get_physical_path(self.folder)
        rid = self.catalog.uids[path]
        self.catalog.uids['/some/other/path'] = rid

        checkup = self.run_checkup()

        self.assertFalse(checkup.is_healthy())
        self.assertEqual(1, len(checkup.aberrations))
        self.assertEqual(
            {
                'paths_tuple_mismatches_uids_tuple',
                'in_uids_keys_not_in_paths_values',
            },
            checkup.get_symptoms(rid))

    def test_detects_missing_entry_in_path_to_rid_mapping(self):
        path = get_physical_path(self.folder)
        rid = self.catalog.uids[path]
        del self.catalog.paths[rid]

        checkup = self.run_checkup()

        self.assertFalse(checkup.is_healthy())
        self.assertEqual(1, len(checkup.aberrations))
        self.assertEqual(
            {
                'in_metadata_keys_not_in_paths_keys',
                'in_uids_keys_not_in_paths_values',
                'in_uids_values_not_in_paths_keys',
            },
            checkup.get_symptoms(rid))
