from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from ftw.catalogdoctor.debug import get_catalog_data
from ftw.catalogdoctor.tests import FunctionalTestCase
from ftw.testing import freeze
from ftw.testing import staticuid
import pytz


class TestDebug(FunctionalTestCase):

    maxDiff = None

    expected = {
        'indexes': {
            'Creator': {'index': {'test_user_1_': 97},
                        'unindex': {97: 'test_user_1_'}
                        },
            'Date': {'index': {1080936000: 97}, 'unindex': {97: 1080936000}},
            'Description': {'docwords': {97: []}},
            'Subject': {'index': {}, 'unindex': {}},
            'Type': {'index': {u'Folder': 97}, 'unindex': {97: u'Folder'}},
            'UID': {'index': {'setUp000000000000000000000000001': 97},
                    'unindex': {97: 'setUp000000000000000000000000001'}},
            'allowedRolesAndUsers': {'index': {'Anonymous': 97},
                                     'unindex': {97: ['Anonymous']}},
            'cmf_uid': {'index': {}, 'unindex': {}},
            'commentators': {'index': {}, 'unindex': {}},
            'created': {'index': {1080936000: 97},
                        'unindex': {97: 1080936000}},
            'effective': {'index': {1055334120: 97},
                          'unindex': {97: 1055334120}},
            'effectiveRange': {'always': [],
                               'since': {},
                               'since_only': {-1560: 97},
                               'unindex': {97: (-1560, None)},
                               'until': {},
                               'until_only': {}},
            'end': {'index': {}, 'unindex': {}},
            'expires': {'index': {1339244520: 97},
                        'unindex': {97: 1339244520}},
            'getId': {'index': {'folder': 97}, 'unindex': {97: 'folder'}},
            'getObjPositionInParent': '<UNSUPPORTED>',
            'getRawRelatedItems': {'index': {}, 'unindex': {}},
            'id': {'index': {'folder': 97}, 'unindex': {97: 'folder'}},
            'in_reply_to': {'index': {}, 'unindex': {}},
            'is_default_page': {'unindex': {97: 0}},
            'is_folderish': {'unindex': {97: 1}},
            'meta_type': {'index': {'Dexterity Container': 97},
                          'unindex': {97: 'Dexterity Container'}},
            'modified': {'index': {1080936000: 97},
                         'unindex': {97: 1080936000}},
            'path': {'index': {(None, 1): 97,
                               ('folder', 1): 97,
                               ('plone', 0): 97},
                     'index_items': {'/plone/folder': 97},
                     'index_parents': {'/plone': 97},
                     'unindex': {97: '/plone/folder'}},
            'portal_type': {'index': {'Folder': 97},
                            'unindex': {97: 'Folder'}},
            'review_state': {'index': {}, 'unindex': {}},
            'sortable_title': {'index': {'folder': 97},
                               'unindex': {97: 'folder'}},
            'start': {'index': {}, 'unindex': {}},
            'sync_uid': {'index': {}, 'unindex': {}},
            'total_comments': {'index': {0: 97}, 'unindex': {97: 0}}
        },
        'paths (rid->path)': {97: '/plone/folder'},
        'uids (path->rid)': {'/plone/folder': 97}
    }

    @staticuid()
    def setUp(self):
        super(TestDebug, self).setUp()

        self.grant('Contributor')
        now = datetime(2017, 10, 16, 0, 0, tzinfo=pytz.utc)
        with freeze(now):
            self.obj = create(Builder('folder').titled(u'Folder'))

    def test_debug_get_catalog_data_rid(self):
        actual = get_catalog_data(rid=self.get_rid(self.obj))
        # interfaces differ between plone versions, just make sure some are
        # there
        self.assertIn(97, actual['indexes']['object_provides']['unindex'])
        self.assertIn('plone.app.contenttypes.interfaces.IFolder',
                      actual['indexes']['object_provides']['index'])
        del actual['indexes']['object_provides']
        # word-ids are different, assert manually
        # 'SearchableText': {'docwords': {97: [256139963, 256139963]}}
        self.assertIn(97, actual['indexes']['SearchableText']['docwords'])
        del actual['indexes']['SearchableText']
        # word-ids are different, assert manually
        # 'Title': {'docwords': {97: [256139963]}}
        self.assertIn(97, actual['indexes']['Title']['docwords'])
        del actual['indexes']['Title']
        self.assertEqual(self.expected, actual)

    def test_debug_get_catalog_data_uid(self):
        actual = get_catalog_data(uid=self.get_physical_path(self.obj))
        # interfaces differ between plone versions, just make sure some are
        # there
        self.assertIn(97, actual['indexes']['object_provides']['unindex'])
        self.assertIn('plone.app.contenttypes.interfaces.IFolder',
                      actual['indexes']['object_provides']['index'])
        del actual['indexes']['object_provides']
        # word-ids are different, assert manually
        # 'SearchableText': {'docwords': {97: [256139963, 256139963]}}
        self.assertIn(97, actual['indexes']['SearchableText']['docwords'])
        del actual['indexes']['SearchableText']
        # word-ids are different, assert manually
        # 'Title': {'docwords': {97: [256139963]}}
        self.assertIn(97, actual['indexes']['Title']['docwords'])
        del actual['indexes']['Title']
        self.assertEqual(self.expected, actual)

    def test_debug_get_catalog_data_limited_indexes(self):
        expected = {
            'indexes': {
                'Type': {'index': {u'Folder': 97}, 'unindex': {97: u'Folder'}},
                'UID': {'index': {'setUp000000000000000000000000001': 97},
                        'unindex': {97: 'setUp000000000000000000000000001'}},
                'portal_type': {'index': {'Folder': 97},
                                'unindex': {97: 'Folder'}},
            },
            'paths (rid->path)': {97: '/plone/folder'},
            'uids (path->rid)': {'/plone/folder': 97}
        }
        actual = get_catalog_data(uid=self.get_physical_path(self.obj),
                                  idxs=['Type', 'UID', 'portal_type'])
        self.assertEqual(expected, actual)

    def test_debug_get_catalog_data_exclusive_parameters(self):
        with self.assertRaises(TypeError):
            get_catalog_data(rid=1234, uid='/something')
