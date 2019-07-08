from BTrees.IIBTree import IITreeSet
from BTrees.OOBTree import OOBTree
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.catalogdoctor.tests import Mock
from ftw.catalogdoctor.utils import contains_or_equals_rid
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid
from Products.PluginIndexes.common.UnIndex import UnIndex


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
