from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.surgery import RemoveExtraRid
from ftw.catalogdoctor.surgery import RemoveOrphanedRid
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

    def test_surgery_remove_extra_rid(self):
        self.make_unhealthy_extra_rid_after_move(self.child)

        result = self.run_healthcheck()
        self.assertFalse(result.is_healthy())
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

        surgery = RemoveExtraRid(self.catalog, unhealthy_rid)
        surgery.perform()

        result = self.run_healthcheck()
        self.assertTrue(result.is_healthy())
