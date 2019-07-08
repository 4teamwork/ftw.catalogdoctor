from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.surgery import UnindexObject
from ftw.catalogdoctor.tests import FunctionalTestCase


class TestUnindexObject(FunctionalTestCase):

    def setUp(self):
        super(TestUnindexObject, self).setUp()

        self.grant('Contributor')
        self.folder = create(Builder('folder').titled(u'Foo')
                             .having(description=u'Lorem ipsum dolor sit'))

    def test_remove_from_zctextindex(self):
        rid = self.get_rid(self.folder)
        index = self.catalog.indexes['SearchableText']

        self.assertTrue(index.index.has_doc(rid))

        surgery = UnindexObject(index, rid)
        surgery.perform()

        self.assertFalse(index.index.has_doc(rid))
