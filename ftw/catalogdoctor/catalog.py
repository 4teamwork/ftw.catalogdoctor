from plone import api


class RidAberration(object):
    """An aberration groups symptoms for a given rid."""

    def __init__(self, rid, path=None):
        self.rid = rid
        self.path = path
        self._catalog_symptoms = dict()

    def report_catalog_symptom(self, name):
        """Report a symptom from the catalog for this abberation."""

        self._catalog_symptoms[name] = True

    @property
    def catalog_symptoms(self):
        return set(self._catalog_symptoms.keys())


class CatalogCheckup(object):
    """Provide health checkup for a Products.ZCatalog.Catalog instance.

    Validates that the catalogs uid and rid mapping and metadata is consistent.
    This means that:
    - the mappings have the same length
    - the mappings are consistent, so every item is in the reverse mapping
    - for every item there is also an entry in the catalog metadata

    It does not validate indices and index data yet.
    """

    def __init__(self, catalog=None):
        self.portal_catalog = catalog or api.portal.get_tool('portal_catalog')
        self.catalog = self.portal_catalog._catalog

        self.aberrations = dict()

    def is_healthy(self):
        """Return whether the catalog is healthy according to this checkup."""

        return not self.aberrations

    def report_aberration(self, rid, path=None):
        """Report an aberration for a rid."""

        if rid not in self.aberrations:
            self.aberrations[rid] = RidAberration(rid, path=path)
        return self.aberrations[rid]

    def report_symptom(self, name, rid, path=None):
        aberration = self.report_aberration(rid, path=path)
        aberration.report_catalog_symptom(name)
        return aberration

    def get_symptoms(self, rid):
        return self.aberrations[rid].catalog_symptoms

    def run(self):
        paths = self.catalog.paths
        paths_values = set(self.catalog.paths.values())

        uids = self.catalog.uids
        uids_values = set(self.catalog.uids.values())

        for path, rid in uids.items():
            if rid not in paths:
                self.report_symptom(
                    'in_uids_values_not_in_paths_keys', rid, path=path)
            elif paths[rid] != path:
                self.report_symptom(
                    'paths_tuple_mismatches_uids_tuple', rid, path=path)

            if path not in paths_values:
                self.report_symptom(
                    'in_uids_keys_not_in_paths_values', rid, path=path)

            if rid not in self.catalog.data:
                self.report_symptom(
                    'in_uids_values_not_in_metadata_keys', rid, path=path)

        for rid, path in paths.items():
            if path not in uids:
                self.report_symptom(
                    'in_paths_values_not_in_uids_keys', rid, path=path)
            elif uids[path] != rid:
                self.report_symptom(
                    'uids_tuple_mismatches_paths_tuple', rid, path=path)

            if rid not in uids_values:
                self.report_symptom(
                    'in_paths_keys_not_in_uids_values', rid, path=path)

            if rid not in self.catalog.data:
                self.report_symptom(
                    'in_paths_keys_not_in_metadata_keys', rid, path=path)

        for rid in self.catalog.data:
            if rid not in paths:
                self.report_symptom(
                    'in_metadata_keys_not_in_paths_keys', rid)
            if rid not in uids_values:
                self.report_symptom(
                    'in_metadata_keys_not_in_uids_values', rid)
