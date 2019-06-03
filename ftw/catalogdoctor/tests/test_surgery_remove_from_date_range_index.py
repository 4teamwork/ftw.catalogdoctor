from datetime import date
from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.surgery import RemoveFromDateRangeIndex
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid


class TestRemoveFromDateRangeIndex(FunctionalTestCase):

    def setUp(self):
        super(TestRemoveFromDateRangeIndex, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))

    def set_effective_range(self, start, end):
        if start is None:
            # bypass getter fallback to FLOOR_DATE
            self.folder.effective = None
        else:
            self.folder.effective_date = start

        if end is None:
            # bypass getter fallback to CEILING_DATE
            self.folder.expires = None
        else:
            self.folder.expiration_date = end
        self.reindex_object(self.folder)

    def test_index_attributes_configured_as_expected_by_tests(self):
        index = self.catalog.indexes['effectiveRange']
        self.assertEqual('effective', index._since_field)
        self.assertEqual('expires', index._until_field)

    def test_remove_from_daterange_index_since_only(self):
        self.set_effective_range(date(2010, 1, 1), None)

        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['effectiveRange']

        self.assertNotIn(rid, index._always)
        self.assertEqual(
            1, len(find_keys_pointing_to_rid(index._since_only, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until_only, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until, rid)))
        self.assertIn(rid, index._unindex)

        surgery = RemoveFromDateRangeIndex(index, rid)
        surgery.perform()

        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since_only, rid)))
        self.assertNotIn(rid, index._unindex)

    def test_remove_from_daterange_index_until_only(self):
        self.set_effective_range(None, date(2016, 12, 1))

        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['effectiveRange']

        self.assertNotIn(rid, index._always)
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since_only, rid)))
        self.assertEqual(
            1, len(find_keys_pointing_to_rid(index._until_only, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until, rid)))
        self.assertIn(rid, index._unindex)

        surgery = RemoveFromDateRangeIndex(index, rid)
        surgery.perform()

        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until_only, rid)))
        self.assertNotIn(rid, index._unindex)

    def test_remove_from_daterange_index_since_until(self):
        self.set_effective_range(date(2010, 7, 7), date(2016, 9, 13))

        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['effectiveRange']

        self.assertNotIn(rid, index._always)
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since_only, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until_only, rid)))
        self.assertEqual(
            1, len(find_keys_pointing_to_rid(index._since, rid)))
        self.assertEqual(
            1, len(find_keys_pointing_to_rid(index._until, rid)))
        self.assertIn(rid, index._unindex)

        surgery = RemoveFromDateRangeIndex(index, rid)
        surgery.perform()

        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until, rid)))
        self.assertNotIn(rid, index._unindex)

    def test_remove_from_daterange_index_always(self):
        self.set_effective_range(None, None)

        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['effectiveRange']

        self.assertIn(rid, index._always)
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since_only, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until_only, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._since, rid)))
        self.assertEqual(
            0, len(find_keys_pointing_to_rid(index._until, rid)))
        self.assertIn(rid, index._unindex)

        surgery = RemoveFromDateRangeIndex(index, rid)
        surgery.perform()

        self.assertNotIn(rid, index._always)
        self.assertNotIn(rid, index._unindex)
