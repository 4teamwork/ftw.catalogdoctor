from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.tests import FunctionalTestCase


class TestDoctorCommand(FunctionalTestCase):

    maxDiff = None

    def setUp(self):
        super(TestDoctorCommand, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))

    def test_healthcheck_healthy_catalog(self):
        expected = [
            'Catalog health check report:',
            'Catalog length is consistent at 1.',
            'Catalog data is healthy.']
        self.assertEqual(expected, self.run_command('doctor', 'healthcheck'))

    def test_healthcheck_unhealthy_catalog(self):
        extra_rid = self.choose_next_rid()
        self.catalog.data[extra_rid] = dict()

        expected = [
            'Catalog health check report:',
            'Inconsistent catalog length:',
            ' claimed length: 1',
            ' uids length: 1',
            ' paths length: 1',
            ' metadata length: 2',
            ' uid index claimed length: 1',
            ' uid index index length: 1',
            ' uid index unindex length: 1',
            'Catalog data is unhealthy, found 1 unhealthy rids:',
            'rid 98 (--no path--):',
            '\t- in_metadata_keys_not_in_paths_keys',
            '\t- in_metadata_keys_not_in_uids_values',
            '',
        ]
        self.assertEqual(expected, self.run_command('doctor', 'healthcheck'))

    def test_surgery_healthy_catlog(self):
        expected = [
            'Catalog health check report:',
            'Catalog length is consistent at 1.',
            'Catalog data is healthy.',
            'Catalog is healthy, no surgery is needed.',
        ]
        self.assertEqual(expected, self.run_command('doctor', 'surgery'))

    def test_surgery_unhealthy_catalog_unfixable_problem(self):
        extra_rid = self.choose_next_rid()
        self.catalog.data[extra_rid] = dict()

        expected = [
            'Catalog health check report:',
            'Inconsistent catalog length:',
            ' claimed length: 1',
            ' uids length: 1',
            ' paths length: 1',
            ' metadata length: 2',
            ' uid index claimed length: 1',
            ' uid index index length: 1',
            ' uid index unindex length: 1',
            'Catalog data is unhealthy, found 1 unhealthy rids:',
            'rid {} (--no path--):'.format(extra_rid),
            '\t- in_metadata_keys_not_in_paths_keys',
            '\t- in_metadata_keys_not_in_uids_values',
            '',
            'Performing surgery:',
            'The following unhealthy rids could not be fixed:',
            'rid {} (--no path--):'.format(extra_rid),
            '\t- in_metadata_keys_not_in_paths_keys',
            '\t- in_metadata_keys_not_in_uids_values',
            '',
            'Not all health problems could be fixed, aborting.'
        ]
        self.assertEqual(expected, self.run_command('doctor', 'surgery'))

    def test_successful_surgery_unhealthy_catalog(self):
        path = self.get_physical_path(self.folder)
        rid = self.catalog.uids.pop(path)
        # drop from uid index index, leave in unindex
        uid_index = self.catalog.indexes['UID']
        uid_index.removeForwardIndexEntry(uid_index._unindex[rid], rid)
        self.portal._delObject(self.folder.getId(), suppress_events=True)

        expected = [
            'Catalog health check report:',
            'Inconsistent catalog length:',
            ' claimed length: 1',
            ' uids length: 0',
            ' paths length: 1',
            ' metadata length: 1',
            ' uid index claimed length: 0',
            ' uid index index length: 0',
            ' uid index unindex length: 1',
            'Catalog data is unhealthy, found 1 unhealthy rids:',
            'rid {} (\'/plone/foo\'):'.format(rid),
            '\t- in_metadata_keys_not_in_uids_values',
            '\t- in_paths_keys_not_in_uids_values',
            '\t- in_paths_values_not_in_uids_keys',
            '\t- in_uuid_unindex_not_in_catalog',
            '\t- in_uuid_unindex_not_in_uuid_index',
            '',
            'Performing surgery:',
            'rid {} (\'/plone/foo\'):'.format(rid),
            '\t- Removed rid from all catalog indexes.',
            '\t- Removed rid from paths (the rid->path mapping).',
            '\t- Removed rid from catalog metadata.',
            '',
            'Performing post-surgery healthcheck:',
            'Catalog health check report:',
            'Catalog length is consistent at 0.',
            'Catalog data is healthy.',
            'Surgery was successful, known health problems could be fixed!',
        ]
        self.assertEqual(expected, self.run_command('doctor', 'surgery'))

    def test_successful_surgery_unhealthy_catalog_dryrun(self):
        path = self.get_physical_path(self.folder)
        rid = self.catalog.uids.pop(path)
        # drop from uid index index, leave in unindex
        uid_index = self.catalog.indexes['UID']
        uid_index.removeForwardIndexEntry(uid_index._unindex[rid], rid)
        self.portal._delObject(self.folder.getId(), suppress_events=True)

        expected = [
            'Performing dryrun!',
            '',
            'Catalog health check report:',
            'Inconsistent catalog length:',
            ' claimed length: 1',
            ' uids length: 0',
            ' paths length: 1',
            ' metadata length: 1',
            ' uid index claimed length: 0',
            ' uid index index length: 0',
            ' uid index unindex length: 1',
            'Catalog data is unhealthy, found 1 unhealthy rids:',
            'rid {} (\'/plone/foo\'):'.format(rid),
            '\t- in_metadata_keys_not_in_uids_values',
            '\t- in_paths_keys_not_in_uids_values',
            '\t- in_paths_values_not_in_uids_keys',
            '\t- in_uuid_unindex_not_in_catalog',
            '\t- in_uuid_unindex_not_in_uuid_index',
            '',
            'Performing surgery:',
            'rid {} (\'/plone/foo\'):'.format(rid),
            '\t- Removed rid from all catalog indexes.',
            '\t- Removed rid from paths (the rid->path mapping).',
            '\t- Removed rid from catalog metadata.',
            '',
            'Performing post-surgery healthcheck:',
            'Catalog health check report:',
            'Catalog length is consistent at 0.',
            'Catalog data is healthy.',
            'Surgery would have been successful, but was aborted due to '
            'dryrun!',
        ]
        self.assertEqual(expected, self.run_command('doctor', '-n', 'surgery'))
