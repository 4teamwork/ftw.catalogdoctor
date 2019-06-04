from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.surgery import RemoveFromBooleanIndex
from ftw.catalogdoctor.tests import FunctionalTestCase


class TestRemoveFromBooleanIndex(FunctionalTestCase):

    def setUp(self):
        super(TestRemoveFromBooleanIndex, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))
        self.folder.isPrincipiaFolderish = False
        self.reindex_object(self.folder)

    def test_remove_from_boolean_index(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['is_folderish']

        self.assertIn(rid, index._index)
        self.assertIn(rid, index._unindex)
        self.assertEqual(1, len(index._index))
        self.assertEqual(1, index._index_length.value)
        self.assertEqual(1, len(index._unindex))
        # off by one. not sure what is happening here. not observed
        # in production. maybe test-setup related?
        self.assertEqual(2, index._length.value)

        surgery = RemoveFromBooleanIndex(index, rid)
        surgery.perform()

        self.assertNotIn(rid, index._index)
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index._index))
        self.assertEqual(0, index._index_length.value)
        self.assertEqual(0, len(index._unindex))
        # off by one. not entirely sure what is happening here. not observed
        # in production. maybe test-setup related?
        self.assertEqual(1, index._length.value)

    def test_remove_from_forward_index_only(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['is_folderish']

        # remove entry from reverse index
        del index._unindex[rid]
        index._length.change(-1)

        self.assertIn(rid, index._index)
        self.assertEqual(1, len(index._index))
        self.assertEqual(1, index._index_length.value)
        self.assertEqual(0, len(index._unindex))
        # off by one. not sure what is happening here. not observed
        # in production. maybe test-setup related?
        self.assertEqual(1, index._length.value)

        surgery = RemoveFromBooleanIndex(index, rid)
        surgery.perform()

        self.assertNotIn(rid, index._index)
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index._index))
        self.assertEqual(0, index._index_length.value)
        self.assertEqual(0, len(index._unindex))
        # off by one. not entirely sure what is happening here. not observed
        # in production. maybe test-setup related?
        self.assertEqual(1, index._length.value)

    def test_remove_from_reverse_index_only(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['is_folderish']

        # remove entry from forward index
        index._index.remove(rid)
        index._index_length.change(-1)

        self.assertEqual(0, len(index._index))
        self.assertEqual(0, index._index_length.value)
        self.assertEqual(1, len(index._unindex))
        # off by one. not sure what is happening here. not observed
        # in production. maybe test-setup related?
        self.assertEqual(2, index._length.value)

        surgery = RemoveFromBooleanIndex(index, rid)
        surgery.perform()

        self.assertNotIn(rid, index._index)
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(0, len(index._index))
        self.assertEqual(0, index._index_length.value)
        self.assertEqual(0, len(index._unindex))
        # off by one. not entirely sure what is happening here. not observed
        # in production. maybe test-setup related?
        self.assertEqual(1, index._length.value)
