from ftw.catalogdoctor.exceptions import CantPerformSurgery
from plone import api
from plone.app.folder.nogopip import GopipIndex
from Products.ExtendedPathIndex.ExtendedPathIndex import ExtendedPathIndex
from Products.PluginIndexes.BooleanIndex.BooleanIndex import BooleanIndex
from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
from Products.PluginIndexes.DateRangeIndex.DateRangeIndex import DateRangeIndex
from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
from Products.PluginIndexes.UUIDIndex.UUIDIndex import UUIDIndex
from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex


# optional collective.indexing support
try:
    from collective.indexing.queue import processQueue
except ImportError:
    def processQueue():
        pass

# optional Products.DateRecurringIndex support
try:
    from Products.DateRecurringIndex.index import DateRecurringIndex
except ImportError:
    class DateRecurringIndex(object):
        pass


class Surgery(object):
    """Surgery can fix a concrete set of symptoms."""

    def __init__(self, catalog, unhealthy_rid):
        self.catalog = catalog
        self.unhealthy_rid = unhealthy_rid
        self.surgery_log = []

    def perform(self):
        raise NotImplementedError

    def unindex_rid_from_all_catalog_indexes(self, rid):
        for idx in self.catalog.indexes.values():
            if isinstance(idx, GopipIndex):
                # Not a real index
                continue

            if isinstance(idx, (ZCTextIndex, DateRangeIndex,
                                DateRecurringIndex, BooleanIndex)):
                # These are more complex index types, that we don't handle
                # on a low level. We have to hope .unindex_object is able
                # to uncatalog the object and doesn't raise a KeyError.
                idx.unindex_object(rid)
                continue

            if not isinstance(idx, (DateIndex, FieldIndex, KeywordIndex,
                                    ExtendedPathIndex, UUIDIndex)):
                raise CantPerformSurgery(
                    'Unhandled index type: {0!r}'.format(idx))

            removed_from_forward_index = False
            entries_pointing_to_rid = [
                val for val, rid_in_index in idx._index.items()
                if rid_in_index == rid]
            if entries_pointing_to_rid:
                # Not quite sure yet if this actually *can* happen
                if len(entries_pointing_to_rid) != 1:
                    raise CantPerformSurgery(
                        'Multiple entries pointing to rid: {}'.format(
                        ' '.join(entries_pointing_to_rid)))
                entry = entries_pointing_to_rid[0]
                del idx._index[entry]
                removed_from_forward_index = True

            if rid in idx._unindex:
                del idx._unindex[rid]

            # The method removeForwardIndexEntry from UnIndex updates the
            # index length. We assume we only have to update the index length
            # when we remove the entry from the forward index, assuming somehow
            # removeForwardIndexEntry has not been called or raised an
            # exception
            if removed_from_forward_index:
                idx._length.change(-1)

        self.surgery_log.append(
            "Removed rid from all catalog indexes.")

    def delete_rid_from_paths(self, rid):
        del self.catalog.paths[rid]

        self.surgery_log.append(
            "Removed rid from paths (the rid->path mapping).")

    def delete_rid_from_metadata(self, rid):
        del self.catalog.data[rid]

        self.surgery_log.append(
            "Removed rid from catalog metadata.")

    def change_catalog_length(self, delta):
        self.catalog._length.change(delta)

    def write_result(self, formatter):
        """Write surgery result to formatter."""

        formatter.info("{}:".format(self.unhealthy_rid))
        for entry in self.surgery_log:
            formatter.info('\t- {}'.format(entry))


class RemoveExtraRid(Surgery):
    """Remove an extra rid from the catalog.

    In this case the object at path still exists but two rids have been
    generated for that object.

    We remove the etra rid from metadata, the rid->path mapping and from
    all indexes.
    """
    def perform(self):
        rid = self.unhealthy_rid.rid
        if len(self.unhealthy_rid.paths) != 1:
            raise CantPerformSurgery(
                "Expected exactly one affected path, got: {}"
                .format(", ".join(self.unhealthy_rid.paths)))

        path = self.unhealthy_rid.paths[0]
        if self.catalog.uids[path] == rid:
            raise CantPerformSurgery(
                "Expected different rid in catalog uids mapping for path {}"
                .format(path))

        self.unindex_rid_from_all_catalog_indexes(rid)
        self.delete_rid_from_paths(rid)
        self.delete_rid_from_metadata(rid)
        self.change_catalog_length(-1)


class RemoveOrphanedRid(Surgery):
    """Remove an orphaned rid from the catalog.

    In this case the object at path no longer exists but the rid still remains
    in the catalog.

    We remove the orphaned rid from metadata, rid->path mapping and from all
    indexes.
    """
    def perform(self):
        rid = self.unhealthy_rid.rid
        if len(self.unhealthy_rid.paths) != 1:
            raise CantPerformSurgery(
                "Expected exactly one affected path, got: {}"
                .format(", ".join(self.unhealthy_rid.paths)))

        path = list(self.unhealthy_rid.paths)[0]
        if path in self.catalog.uids:
            raise CantPerformSurgery(
                "Expected path to be absent from catalog uids {}"
                .format(path))

        portal = api.portal.get()
        obj = portal.unrestrictedTraverse(path, None)
        if obj is not None:
            raise CantPerformSurgery(
                "Unexpectedly found object at {}".format(path))

        self.unindex_rid_from_all_catalog_indexes(rid)
        self.delete_rid_from_paths(rid)
        self.delete_rid_from_metadata(rid)
        self.change_catalog_length(-1)


class CatalogDoctor(object):
    """Performs surgery for an unhealthy_rid, if possible.

    Surgeries are assigned based on symptoms. For each set of symptoms a
    surgical procedure can be registered. This decides if an unhealthy rid can
    be treated.
    """
    surgeries = {
        (
            'in_metadata_keys_not_in_uids_values',
            'in_paths_keys_not_in_uids_values',
            'in_uuid_unindex_not_in_catalog',
            'in_uuid_unindex_not_in_uuid_index',
            'uids_tuple_mismatches_paths_tuple',
        ): RemoveExtraRid,
        (
            'in_metadata_keys_not_in_uids_values',
            'in_paths_keys_not_in_uids_values',
            'in_paths_values_not_in_uids_keys',
            'in_uuid_unindex_not_in_catalog',
            'in_uuid_unindex_not_in_uuid_index',
        ): RemoveOrphanedRid,
    }

    def __init__(self, catalog, unhealthy_rid):
        self.catalog = catalog
        self.unhealthy_rid = unhealthy_rid

    def can_perform_surgery(self):
        return bool(self.get_surgery())

    def get_surgery(self):
        symptoms = self.unhealthy_rid.catalog_symptoms
        return self.surgeries.get(symptoms, None)

    def perform_surgery(self):
        surgery_cls = self.get_surgery()
        if not surgery_cls:
            return None

        surgery = surgery_cls(self.catalog, self.unhealthy_rid)
        surgery.perform()
        return surgery
