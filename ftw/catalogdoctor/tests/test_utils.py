from BTrees.IIBTree import IITreeSet
from BTrees.OOBTree import OOBTree
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.tests import Mock
from ftw.catalogdoctor.utils import contains_or_equals_rid
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid
from ftw.catalogdoctor.utils import is_shorter_path_to_same_file
from Products.PluginIndexes.common.UnIndex import UnIndex
from unittest import TestCase


class TestFindKeysPointingToRid(FunctionalTestCase):

    def test_find_keys_pointing_to_rid(self):
        dictish = {'foo': [1, 77, 678],
                   'bar': [3, 77],
                   'qux': []}

        self.assertItemsEqual(
            ['foo', 'bar'], find_keys_pointing_to_rid(dictish, 77))

    def test_find_keys_pointing_to_rid_single_value(self):
        dictish = {'foo': 1,
                   'bar': -23}

        self.assertItemsEqual(
            ['bar'], find_keys_pointing_to_rid(dictish, -23))

    def test_find_keys_pointing_to_rid_emtpy_result(self):
        dictish = {'foo': [1, 77],
                   'qux': []}

        self.assertItemsEqual(
            [], find_keys_pointing_to_rid(dictish, 1337))

    def test_btrees_find_keys_in_pointing_to_rid(self):
        dictish = OOBTree({'foo': IITreeSet((5, -17, 43)),
                           'bar': IITreeSet(),
                           'somekey': IITreeSet((-17, 1))})

        self.assertItemsEqual(
            ['foo', 'somekey'], find_keys_pointing_to_rid(dictish, -17))

    def test_unindex_find_keys_pointing_to_rid(self):
        mock = Mock()
        mock.foo = 'a key'
        index = UnIndex('foo')
        index.index_object(-12, mock)

        self.assertItemsEqual(['a key'], find_keys_pointing_to_rid(index, -12))


class TestContainsOrEqualsRid(FunctionalTestCase):

    def test_contains_rid_truthy_set(self):
        self.assertTrue(contains_or_equals_rid(123, set((123, 45, -7))))

    def test_contains_rid_falsy_set(self):
        self.assertFalse(contains_or_equals_rid(3, set((123, 45, -7))))

    def test_contains_rid_truthy_treeset(self):
        self.assertTrue(contains_or_equals_rid(-3, IITreeSet((10, 33, -3))))

    def test_contains_rid_falsy_treeset(self):
        self.assertFalse(contains_or_equals_rid(-3, IITreeSet((10, 33, -103))))

    def test_equals_rid_truthy(self):
        self.assertTrue(contains_or_equals_rid(123, 123))

    def test_equals_rid_false(self):
        self.assertFalse(contains_or_equals_rid(123, 77))


class TestIsShorterPath(TestCase):

    def test_truthy_is_shorter_path_trailing_leading_slashes_ignored(self):
        self.assertTrue(
            is_shorter_path_to_same_file('bar', 'foo/bar'))
        self.assertTrue(
            is_shorter_path_to_same_file('bar', '/foo/bar'))
        self.assertTrue(
            is_shorter_path_to_same_file('bar', '/foo/bar/'))
        self.assertTrue(
            is_shorter_path_to_same_file('/bar', 'foo/bar'))
        self.assertTrue(
            is_shorter_path_to_same_file('/bar', '/foo/bar'))
        self.assertTrue(
            is_shorter_path_to_same_file('/bar', '/foo/bar/'))
        self.assertTrue(
            is_shorter_path_to_same_file('/bar/', 'foo/bar'))
        self.assertTrue(
            is_shorter_path_to_same_file('/bar/', '/foo/bar'))
        self.assertTrue(
            is_shorter_path_to_same_file('/bar/', '/foo/bar/'))

    def test_truthy_is_shorter_path_several_segments_shorter(self):
        self.assertTrue(
            is_shorter_path_to_same_file('/bar/', '/foo/bar/'))
        self.assertTrue(
            is_shorter_path_to_same_file('/bar/', 'foo/qux/bar'))
        self.assertTrue(
            is_shorter_path_to_same_file('bar/', '/foo/1/2/4/bar'))

    def test_falsy_is_shorter_path_same_path(self):
        self.assertFalse(
            is_shorter_path_to_same_file('foo/bar', 'foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/bar', 'foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('foo/bar/', 'foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/bar/', 'foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('foo/bar', 'foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/bar', '/foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/bar', 'foo/bar/'))
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/bar/', '/foo/bar/'))

    def test_falsy_is_shorter_path_longer_path(self):
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/qux/bar', '/foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/1/2/3/4/bar', '/foo/bar'))

    def test_falsy_is_shorter_path_different_path(self):
        self.assertFalse(
            is_shorter_path_to_same_file('/foo', '/foo/bar'))
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/quxbar', '/foo/bar'))

    def test_falsy_is_shorter_path_different_order(self):
        self.assertFalse(
            is_shorter_path_to_same_file('/foo/1/zwo/bar', '/foo/zwo/1/bar'))
