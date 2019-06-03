from datetime import date
from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.compat import DateRecurringIndex
from ftw.catalogdoctor.surgery import RemoveFromUnIndex
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid
from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex


class TestRemoveFromUnIndex(FunctionalTestCase):

    def setUp(self):
        super(TestRemoveFromUnIndex, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))

    def test_remove_object_from_reverse_index_only(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['Type']

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(1, len(entries_pointing_to_rid))
        self.assertIn(rid, index._unindex)
        self.assertEqual(1, len(index))

        del index._index[entries_pointing_to_rid[0]]
        index._length.change(-1)

        surgery = RemoveFromUnIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))

    def test_remove_object_from_forward_index_only(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['Type']

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(1, len(entries_pointing_to_rid))
        self.assertIn(rid, index._unindex)
        self.assertEqual(1, len(index))

        del index._unindex[rid]

        surgery = RemoveFromUnIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))

    def test_remove_healthy_object_from_fieldindex(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['Type']
        self.assertIs(FieldIndex, type(index))

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(1, len(entries_pointing_to_rid))
        self.assertIn(rid, index._unindex)
        self.assertEqual(1, len(index))

        surgery = RemoveFromUnIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))

    def test_remove_healthy_object_from_dateindex(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['modified']
        self.assertIs(DateIndex, type(index))

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(1, len(entries_pointing_to_rid))
        self.assertIn(rid, index._unindex)
        self.assertEqual(1, len(index))

        surgery = RemoveFromUnIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))

    def test_remove_healthy_object_from_daterecurringindex(self):
        # pretend we are something that supports recurring dates
        self.folder.start = date(2010, 1, 1)
        self.folder.recurrence = 'FREQ=DAILY;INTERVAL=1;COUNT=5'
        self.reindex_object(self.folder)

        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['start']
        self.assertIs(DateRecurringIndex, type(index))

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(5, len(entries_pointing_to_rid))
        self.assertIn(rid, index._unindex)
        self.assertEqual(5, len(index))

        surgery = RemoveFromUnIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))

    def test_remove_healthy_object_from_keywordindex(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['object_provides']
        self.assertIs(KeywordIndex, type(index))

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertGreater(len(entries_pointing_to_rid), 0)
        self.assertIn(rid, index._unindex)
        self.assertGreater(len(index), 0)

        surgery = RemoveFromUnIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))
