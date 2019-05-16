from ftw.catalogdoctor.exceptions import CantPerformSurgery


class RemoveExtraRid(object):
    """Remove an extra rid from the catalog."""

    def __init__(self, catalog, unhealthy_rid):
        self.catalog = catalog
        self.unhealthy_rid = unhealthy_rid

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

        for index in self.catalog.indexes.values():
            index.unindex_object(rid)  # fail in case of no `unindex_object`
        del self.catalog.paths[rid]
        del self.catalog.data[rid]
        self.catalog._length.change(-1)

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
         ): RemoveExtraRid
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
