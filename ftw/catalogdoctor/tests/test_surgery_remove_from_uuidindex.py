from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.surgery import RemoveFromUUIDIndex
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid


class TestRemoveFromUUIDIndex(FunctionalTestCase):

    def setUp(self):
        super(TestRemoveFromUUIDIndex, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))

    def test_remove_healthy_object(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['UID']

        entries_pointing_to_rid = find_keys_pointing_to_rid(index._index, rid)
        self.assertEqual(1, len(entries_pointing_to_rid))
        self.assertIn(rid, index._unindex)
        self.assertEqual(1, len(index))

        surgery = RemoveFromUUIDIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index._index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))

    def test_remove_from_reverse_index_only(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['UID']

        entries_pointing_to_rid = find_keys_pointing_to_rid(index._index, rid)
        del index._index[entries_pointing_to_rid[0]]
        index._length.change(-1)

        self.assertIn(rid, index._unindex)
        self.assertEqual(1, len(index._unindex))

        surgery = RemoveFromUUIDIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index._index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))

    def test_remove_from_forward_index_only(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['UID']

        del index._unindex[rid]

        entries_pointing_to_rid = find_keys_pointing_to_rid(index._index, rid)
        self.assertEqual(1, len(entries_pointing_to_rid))
        self.assertEqual(1, len(index._index))

        surgery = RemoveFromUUIDIndex(index, rid)
        surgery.perform()

        entries_pointing_to_rid = find_keys_pointing_to_rid(index._index, rid)
        self.assertEqual(0, len(entries_pointing_to_rid))
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index))
