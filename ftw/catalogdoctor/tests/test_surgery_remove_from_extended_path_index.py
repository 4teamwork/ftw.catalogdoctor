from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.surgery import RemoveFromExtendedPathIndex
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid


class TestRemoveFromExtendedPathIndex(FunctionalTestCase):

    def setUp(self):
        super(TestRemoveFromExtendedPathIndex, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo'))
        self.child_folder = create(Builder('folder').titled(u'Child').within(self.folder))
        self.sibling_folder = create(Builder('folder').titled(u'Sibling'))

    def test_remove_parent_from_extended_path_index(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['path']

        # _index
        self.assertIn(rid, index._index['plone'][0])  # plone site at level 0
        self.assertIn(rid, index._index['foo'][1])  # object id at level 1
        self.assertIn(rid, index._index[None][1])  # terminator at level 1
        self.assertEqual(5, len(index._index))  # 3 objects, plone, terminator
        # _index_items
        items_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_items, rid)
        self.assertEqual(1, len(items_pointing_to_rid))
        self.assertEqual(3, len(index._index_items))
        # _index_parents
        parents_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_parents, rid)
        self.assertEqual(1, len(parents_pointing_to_rid))
        self.assertEqual(2, len(index._index_parents))
        # _unindex
        self.assertIn(rid, index._unindex)
        self.assertEqual(3, len(index._unindex))
        # index stats
        self.assertEqual(3, len(index))

        surgery = RemoveFromExtendedPathIndex(index, rid)
        surgery.perform()

        # _index
        self.assertNotIn(rid, index._index['plone'][0])
        #  foo itself remains as it has children
        self.assertNotIn(rid, index._index['foo'][1])
        self.assertNotIn(rid, index._index[None][1])
        #  length remains as we removed an object with children
        self.assertEqual(5, len(index._index))
        # _index_items
        items_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_items, rid)
        self.assertEqual(0, len(items_pointing_to_rid))
        self.assertEqual(2, len(index._index_items))
        # _index_parents
        parents_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_parents, rid)
        self.assertEqual(0, len(parents_pointing_to_rid))
        self.assertEqual(2, len(index._index_parents))
        # _unindex
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(2, len(index._unindex))
        # index stats
        self.assertEqual(2, len(index))

    def test_remove_child_from_extended_path_index(self):
        rid = self.get_rid(self.child_folder)
        index = self.catalog.indexes['path']

        # _index
        self.assertIn(rid, index._index['plone'][0])  # plone site at level 0
        self.assertIn(rid, index._index['foo'][1])  # parent id at level 1
        self.assertIn(rid, index._index['child'][2])  # object id at level 2
        self.assertIn(rid, index._index[None][2])  # terminator at level 2
        self.assertEqual(5, len(index._index))  # 3 objects, plone, terminator
        # _index_items
        items_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_items, rid)
        self.assertEqual(1, len(items_pointing_to_rid))
        self.assertEqual(3, len(index._index_items))
        # _index_parents
        parents_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_parents, rid)
        self.assertEqual(1, len(parents_pointing_to_rid))
        self.assertEqual(2, len(index._index_parents))
        # _unindex
        self.assertIn(rid, index._unindex)
        self.assertEqual(3, len(index._unindex))
        # index stats
        self.assertEqual(3, len(index))

        surgery = RemoveFromExtendedPathIndex(index, rid)
        surgery.perform()

        # _index
        self.assertNotIn(rid, index._index['plone'][0])
        self.assertNotIn(rid, index._index['foo'][1])
        #  child is dropped as it is without children
        self.assertNotIn('child', index._index)
        #  2nd level terminator is dropped as there are no more entries
        self.assertNotIn(2, index._index[None])
        self.assertEqual(4, len(index._index))
        # _index_items
        items_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_items, rid)
        self.assertEqual(0, len(items_pointing_to_rid))
        self.assertEqual(2, len(index._index_items))
        # _index_parents
        parents_pointing_to_rid = find_keys_pointing_to_rid(
            index._index_parents, rid)
        self.assertEqual(0, len(parents_pointing_to_rid))
        # '/plone' is the only remaining parent
        self.assertEqual(1, len(index._index_parents))
        # _unindex
        self.assertNotIn(rid, index._unindex)
        self.assertEqual(2, len(index._unindex))
        # index stats
        self.assertEqual(2, len(index))
