from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.tests import get_physical_path
from StringIO import StringIO
import logging


class TestCatalogHealthCheck(FunctionalTestCase):

    def setUp(self):
        super(TestCatalogHealthCheck, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))

    def test_initial_catalog_is_healthy(self):
        result = self.run_healthcheck()

        self.assertTrue(result.is_healthy())
        self.assertTrue(result.is_length_healthy())

    def test_unhealthy_rids_make_catalog_unhealthy(self):
        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())

        result.report_symptom('foo', self.choose_next_rid())
        self.assertFalse(result.is_healthy())

    def test_longer_uids_make_catalog_unhealthy(self):
        self.catalog.uids['foo'] = self.choose_next_rid()

        result = self.run_healthcheck()
        self.assertFalse(result.is_length_healthy())

    def test_longer_paths_make_catalog_unhealthy(self):
        self.catalog.paths[self.choose_next_rid()] = 'foo'

        result = self.run_healthcheck()
        self.assertFalse(result.is_length_healthy())

    def test_longer_metadata_make_catalog_unhealthy(self):
        self.catalog.data[self.choose_next_rid()] = dict()

        result = self.run_healthcheck()
        self.assertFalse(result.is_length_healthy())

    def test_detects_duplicate_entry_in_rid_to_path_mapping_keys(self):
        broken_rid = self.choose_next_rid()
        self.catalog.paths[broken_rid] = get_physical_path(self.folder)
        self.catalog._length.change(1)

        result = self.run_healthcheck()

        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(
            (
                'in_paths_keys_not_in_metadata_keys',
                'in_paths_keys_not_in_uids_values',
                'uids_tuple_mismatches_paths_tuple',
            ),
            result.get_symptoms(broken_rid))

    def test_detects_extra_entry_in_rid_to_path_mapping(self):
        extra_rid = self.choose_next_rid()
        self.catalog.paths[extra_rid] = '/foo'
        self.catalog._length.change(1)

        result = self.run_healthcheck()

        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(
            (
                'in_paths_keys_not_in_metadata_keys',
                'in_paths_keys_not_in_uids_values',
                'in_paths_values_not_in_uids_keys',
            ),
            result.get_symptoms(extra_rid))

    def test_detects_missing_entry_in_rid_to_path_mapping_values(self):
        path = get_physical_path(self.folder)
        rid = self.catalog.uids.pop(path)

        result = self.run_healthcheck()

        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(
            (
                'in_metadata_keys_not_in_uids_values',
                'in_paths_keys_not_in_uids_values',
                'in_paths_values_not_in_uids_keys',
            ),
            result.get_symptoms(rid))

    def test_detects_duplicate_entry_in_path_to_rid_mapping(self):
        path = get_physical_path(self.folder)
        rid = self.catalog.uids[path]
        self.catalog.uids['/some/other/path'] = rid

        result = self.run_healthcheck()

        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(
            (
                'in_uids_keys_not_in_paths_values',
                'paths_tuple_mismatches_uids_tuple',
            ),
            result.get_symptoms(rid))

    def test_detects_missing_entry_in_path_to_rid_mapping(self):
        path = get_physical_path(self.folder)
        rid = self.catalog.uids[path]
        del self.catalog.paths[rid]

        result = self.run_healthcheck()

        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(
            (
                'in_metadata_keys_not_in_paths_keys',
                'in_uids_keys_not_in_paths_values',
                'in_uids_values_not_in_paths_keys',
            ),
            result.get_symptoms(rid))

    def test_detects_extra_entry_in_path_to_rid_mapping(self):
        extra_rid = self.choose_next_rid()
        self.catalog.uids['/foo'] = extra_rid

        result = self.run_healthcheck()

        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(
            (
                'in_uids_keys_not_in_paths_values',
                'in_uids_values_not_in_metadata_keys',
                'in_uids_values_not_in_paths_keys',
            ),
            result.get_symptoms(extra_rid))

    def test_detects_extra_entry_in_metadata(self):
        extra_rid = self.choose_next_rid()
        self.catalog.data[extra_rid] = dict()

        result = self.run_healthcheck()

        self.assertFalse(result.is_healthy())
        self.assertEqual(1, len(result.unhealthy_rids))
        self.assertEqual(
            (
                'in_metadata_keys_not_in_paths_keys',
                'in_metadata_keys_not_in_uids_values',
            ),
            result.get_symptoms(extra_rid))

    def test_logging(self):
        extra_rid = self.choose_next_rid()
        self.catalog.data[extra_rid] = dict()

        result = self.run_healthcheck()

        log = StringIO()
        loghandler = logging.StreamHandler(log)
        logger = logging.getLogger('ftw.catalogdoctor')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(loghandler)

        result.write_result(logger)
        expected = [
            'Catalog health check report:',
            'Inconsistent catalog length:',
            ' claimed length: 1',
            ' uids length: 1',
            ' paths length: 1',
            ' metadata length: 2',
            'Index data is unhealthy, found 1 unhealthy rids:',
            'rid: 98 (--no path--)',
            '\t- in_metadata_keys_not_in_paths_keys',
            '\t- in_metadata_keys_not_in_uids_values',
            '',
        ]
        self.assertEqual(expected, log.getvalue().splitlines())