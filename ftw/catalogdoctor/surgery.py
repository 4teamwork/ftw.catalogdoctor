from ftw.catalogdoctor.exceptions import CantPerformSurgery
from plone import api


class Surgery(object):
    """Surgery can fix a concrete set of symptoms."""

    def __init__(self, catalog, unhealthy_rid):
        self.catalog = catalog
        self.unhealthy_rid = unhealthy_rid

    def perform(self):
        raise NotImplementedError

    def unindex_rid_from_all_catalog_indexes(self, rid):
        for index in self.catalog.indexes.values():
            index.unindex_object(rid)  # fail in case of no `unindex_object`

    def delete_rid_from_paths(self, rid):
        del self.catalog.paths[rid]

    def delete_rid_from_metadata(self, rid):
        del self.catalog.data[rid]

    def change_catalog_length(self, delta):
        self.catalog._length.change(delta)


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

        path = list(self.unhealthy_rid.paths)[0]
        if self.catalog.uids[path] == rid:
            raise CantPerformSurgery(
                "Expected different rid in catalog uids mapping for path {}"
                .format(path))

        self.unindex_rid_from_all_catalog_indexes(rid)
        self.delete_rid_from_paths(rid)
        self.delete_rid_from_metadata(rid)
        self.change_catalog_length(-1)

        return "Removed {} from catalog.".format(rid)


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

        return "Removed {} from catalog.".format(rid)


class CatalogDoctor(object):
    """Performs surgery for an unhealthy_rid, if possible.

    Surgeries are assigned based on symptoms. For each set of symptoms a
    surgical procedure can be registered. This decides if an unhealthy rid can
    be treated.
    """
    surgeries = {
        ('in_metadata_keys_not_in_uids_values',
         'in_paths_keys_not_in_uids_values',
         'uids_tuple_mismatches_paths_tuple',
         ): RemoveExtraRid,
        ('in_metadata_keys_not_in_uids_values',
         'in_paths_keys_not_in_uids_values',
         'in_paths_values_not_in_uids_keys'
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
        surgery = self.get_surgery()
        if not surgery:
            return None

        return surgery(self.catalog, self.unhealthy_rid).perform()
