from Acquisition import aq_chain
from Acquisition import aq_inner
from ftw.catalogdoctor.compat import DateRecurringIndex
from ftw.catalogdoctor.exceptions import CantPerformSurgery
from ftw.catalogdoctor.utils import find_keys_pointing_to_rid
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


class SurgeryStep(object):

    def __init__(self, index, rid):
        self.index = index
        self.rid = rid

    def _remove_keys_pointing_to_rid(self, index, linked_length=None):
        """Remove all entries pointing to rid from a forward index.

        Rows in indices are expected to be a set, e.g. a `TreeSet`. Once the
        set is emtpy it should also be removed from the index.

        If `linked_length` is provided it is decreased when a row is removed.

        """
        for key in find_keys_pointing_to_rid(index, self.rid):
            row = index[key]
            row.remove(self.rid)
            if not row:
                del index[key]
                if linked_length:
                    linked_length.change(-1)

    def _remove_rid_from_unindex(self, unindex):
        """Remove rid from a reverse index."""

        if self.rid in unindex:
            del unindex[self.rid]

    def perform(self):
        raise NotImplementedError


class NullStep(SurgeryStep):
    """Don't do anything."""

    def perform(self):
        pass


class RemoveFromUUIDIndex(SurgeryStep):
    """Remove rid from a `UUIDIndex`."""

    def _remove_keys_pointing_to_rid(self, index, linked_length=None):
        for key in find_keys_pointing_to_rid(index, self.rid):
            del index[key]
            self.index._length.change(-1)

    def perform(self):
        self._remove_keys_pointing_to_rid(self.index._index)
        self._remove_rid_from_unindex(self.index._unindex)


class RemoveFromUnIndex(SurgeryStep):
    """Remove a rid from a simple forward and reverse index."""

    def perform(self):
        self._remove_keys_pointing_to_rid(
            self.index._index, linked_length=self.index._length)
        self._remove_rid_from_unindex(self.index._unindex)


class RemoveFromDateRangeIndex(SurgeryStep):
    """Remove rid from a `DateRangeIndex`."""

    def perform(self):
        if self.rid in self.index._always:
            self.index._always.remove(self.rid)

        for index in (
                self.index._since_only,
                self.index._until_only,
                self.index._since,
                self.index._until):
            self._remove_keys_pointing_to_rid(index)

        self._remove_rid_from_unindex(self.index._unindex)


class RemoveFromBooleanIndex(SurgeryStep):
    """Remove rid from a `BooleanIndex`.

    Lazily skips checking whether the boolean index should be inverted or not,
    as this operation is  functionally irrelevant and will happen during the
    next reindex operation by plone.
    """
    def perform(self):
        if self.rid in self.index._unindex:
            del self.index._unindex[self.rid]
            self.index._length.change(-1)

        if self.rid in self.index._index:
            self.index._index.remove(self.rid)
            self.index._index_length.change(-1)


class RemoveFromExtendedPathIndex(SurgeryStep):
    """Remove rid from a `ExtendedPathIndex`."""

    def perform(self):
        # _index
        components_with_rid = []
        for component, level_to_rid in self.index._index.items():
            for level, rids in level_to_rid.items():
                if self.rid in rids:
                    components_with_rid.append((component, level,))

        for component, level in components_with_rid:
            self.index._index[component][level].remove(self.rid)
            if not self.index._index[component][level]:
                del self.index._index[component][level]
            if not self.index._index[component]:
                del self.index._index[component]

        # _index_items
        for key in find_keys_pointing_to_rid(self.index._index_items, self.rid):
            del self.index._index_items[key]

        # _index_parents
        self._remove_keys_pointing_to_rid(self.index._index_parents)

        # _unindex
        if self.rid in self.index._unindex:
            del self.index._unindex[self.rid]
            self.index._length.change(-1)


class UnindexObject(SurgeryStep):
    """Remove a rid via the official `unindex_object` API."""

    def perform(self):
        self.index.unindex_object(self.rid)


class Surgery(object):
    """Surgery can fix a concrete set of symptoms."""

    index_to_step = {
        BooleanIndex: RemoveFromBooleanIndex,
        DateIndex: RemoveFromUnIndex,
        DateRangeIndex: RemoveFromDateRangeIndex,
        DateRecurringIndex: RemoveFromUnIndex,
        ExtendedPathIndex: RemoveFromExtendedPathIndex,
        FieldIndex: RemoveFromUnIndex,
        GopipIndex: NullStep,  # not a real index
        KeywordIndex: RemoveFromUnIndex,
        UUIDIndex: RemoveFromUUIDIndex,
        ZCTextIndex: UnindexObject,
    }

    def __init__(self, catalog, unhealthy_rid):
        self.catalog = catalog
        self.unhealthy_rid = unhealthy_rid
        self.surgery_log = []

    def perform(self):
        raise NotImplementedError

    def unindex_rid_from_all_catalog_indexes(self, rid):
        for idx in self.catalog.indexes.values():
            surgery_step = self.index_to_step.get(type(idx))

            if not surgery_step:
                raise CantPerformSurgery(
                    'Unhandled index type: {0!r}'.format(idx))

            surgery_step(idx, rid).perform()

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

    def delete_path_from_uids(self, path):
        del self.catalog.uids[path]

        self.surgery_log.append(
            "Removed path from uids (the path->rid mapping).")

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


class ReindexMissingUUID(Surgery):
    """Reindex an uuid which is partially missing from the UID index.

    Removing and reindexing the object seems to do the trick in such cases.
    """
    def perform(self):
        rid = self.unhealthy_rid.rid

        if len(self.unhealthy_rid.paths) != 1:
            raise CantPerformSurgery(
                "Expected exactly one affected path, got: {}"
                .format(", ".join(self.unhealthy_rid.paths)))

        path = list(self.unhealthy_rid.paths)[0]

        portal = api.portal.get()
        obj = portal.unrestrictedTraverse(path, None)
        if obj is None:
            raise CantPerformSurgery(
                "Missing object at {}".format(path))

        # update UID index
        index = self.catalog.indexes['UID']
        RemoveFromUUIDIndex(index, rid).perform()
        index.index_object(rid, obj)

        # make sure catalog metadata is up to date as well
        self.catalog.updateMetadata(obj, path, rid)

        self.surgery_log.append("Reindexed UID index and updated metadata.")


class RemoveRidOrReindexObject(Surgery):
    """Reindex an object for all indexes or remove the stray rid.

    This can have two causes:
    - Either there are orphaned rids left behind in the catalogs `uid` and
      `path` mappings. In such cases the referenced object is is no longer
      traversable as plone content and we can remove the orphaned rid.
    - Special case of above when the object has been moved into its parents. In
      such cases the object can still be traversed as object is found via
      acquisition. We can remove the orphaned rid in such cases.
    - The object has not been indexed correctly, in such cases the object can
      be traversed and has to be reindexed in all indexes.

    """
    def perform(self):
        rid = self.unhealthy_rid.rid

        if rid not in self.catalog.data:
            raise CantPerformSurgery(
                "Expected rid to be present in catalog metadata {}"
                .format(rid))

        if len(self.unhealthy_rid.paths) != 1:
            raise CantPerformSurgery(
                "Expected exactly one affected path, got: {}"
                .format(", ".join(self.unhealthy_rid.paths)))

        if rid not in self.catalog.paths:
            raise CantPerformSurgery(
                "Expected rid to be present in catalog paths {}"
                .format(rid))

        path = list(self.unhealthy_rid.paths)[0]
        if path not in self.catalog.uids:
            raise CantPerformSurgery(
                "Expected path to be present in catalog uids {}"
                .format(path))

        portal = api.portal.get()
        obj = portal.unrestrictedTraverse(path, None)

        # the object is gone
        if obj is None:
            self.unindex_rid_from_all_catalog_indexes(rid)
            self.delete_rid_from_paths(rid)
            self.delete_rid_from_metadata(rid)
            self.delete_path_from_uids(path)
            self.change_catalog_length(-1)

            return

        # special case when the object has been moved into one of its parents.
        # it can be traversed as it is found via acquisition. safeguard so we
        # only unindex objects where this special case is true.
        obj_path = '/'.join(obj.getPhysicalPath())
        if obj_path != path:
            if aq_chain(aq_inner(obj))[1:] == aq_chain(obj)[1:]:
                raise CantPerformSurgery(
                    "Object path after traversing {} differs from path before "
                    "traversing and in catalog {}, but acquisition chain "
                    "is unexpectedly equal.".format(obj_path, path))

            self.unindex_rid_from_all_catalog_indexes(rid)
            self.delete_rid_from_paths(rid)
            self.delete_rid_from_metadata(rid)
            self.delete_path_from_uids(path)
            self.change_catalog_length(-1)

            return

        # the object is still there and somehow vanished from the indexes.
        # we reindex to update indexes and metadata.
        obj.reindexObject()
        self.surgery_log.append("Reindexed object.")


class CatalogDoctor(object):
    """Performs surgery for an unhealthy_rid, if possible.

    Surgeries are assigned based on symptoms. For each set of symptoms a
    surgical procedure can be registered. This decides if an unhealthy rid can
    be treated.

    When you add symptom tuples to surgeries make sure they are sorted
    alphabetically.
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
            'uids_tuple_mismatches_paths_tuple',
        ): RemoveExtraRid,
        (
            'in_metadata_keys_not_in_uids_values',
            'in_paths_keys_not_in_uids_values',
            'in_paths_values_not_in_uids_keys',
        ): RemoveOrphanedRid,
        (
            'in_metadata_keys_not_in_uids_values',
            'in_paths_keys_not_in_uids_values',
            'in_paths_values_not_in_uids_keys',
            'in_uuid_unindex_not_in_catalog',
            'in_uuid_unindex_not_in_uuid_index',
        ): RemoveOrphanedRid,
        (
            'in_catalog_not_in_uuid_index',
            'in_uuid_unindex_not_in_uuid_index',
        ): ReindexMissingUUID,
        (
            'in_catalog_not_in_uuid_index',
            'in_catalog_not_in_uuid_unindex',
        ): RemoveRidOrReindexObject,
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
