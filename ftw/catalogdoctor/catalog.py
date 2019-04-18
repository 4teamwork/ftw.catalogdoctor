from plone import api
from ftw.catalogdoctor.exceptions import CantPerformSurgery


class RidAberration(object):
    """An aberration represents issues with a certain rid.

    It provides methods to register certain symtomps that were found in the
    catalog for its rid and thus is groups all symptoms for a given rid.
    """
    def __init__(self, rid):
        self.rid = rid
        self.paths = set()
        self._catalog_symptoms = dict()

    def attach_path(self, path):
        self.paths.add(path)

    def report_catalog_symptom(self, name):
        """Report a symptom from the catalog for this abberation."""

        self._catalog_symptoms[name] = True

    @property
    def catalog_symptoms(self):
        return tuple(sorted(self._catalog_symptoms.keys()))

    def write_result(self, formatter):
        if self.paths:
            paths = ", ".join("'{}'".format(p) for p in self.paths)
        else:
            paths = "--no path--"
        formatter.info("rid: {} ({})".format(self.rid, paths))
        for symptom in self.catalog_symptoms:
            formatter.info('\t- {}'.format(symptom))


class CheckupResult(object):
    """Provide health result for one catalog checkup run."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.aberrations = dict()
        self.claimed_length = None
        self.uids_length = None
        self.paths_length = None
        self.data_length = None

    def get_aberrations(self):
        return self.aberrations.values()

    def report_catalog_stats(self, claimed_length, uids_length, paths_length, data_length):
        self.claimed_length = claimed_length
        self.uids_length = uids_length
        self.paths_length = paths_length
        self.data_length = data_length

    def report_aberration(self, rid, path=None):
        """Report an aberration for a rid."""

        if rid not in self.aberrations:
            self.aberrations[rid] = RidAberration(rid)

        aberration = self.aberrations[rid]
        if path:
            aberration.attach_path(path)
        return aberration

    def report_symptom(self, name, rid, path=None):
        aberration = self.report_aberration(rid, path=path)
        aberration.report_catalog_symptom(name)
        return aberration

    def get_symptoms(self, rid):
        return self.aberrations[rid].catalog_symptoms

    def is_healthy(self):
        """Return whether the catalog is healthy according to this result."""

        return self.is_index_data_healthy() and self.is_length_healthy()

    def is_index_data_healthy(self):
        return not self.aberrations

    def is_length_healthy(self):
        return (
            self.claimed_length
            == self.uids_length
            == self.paths_length
            == self.data_length
        )

    def write_result(self, formatter):
        """Log result to logger."""

        formatter.info("Catalog health checkup report:")

        if self.is_length_healthy():
            formatter.info(
                "Catalog length is consistent at {}.".format(
                    self.claimed_length))
        else:
            formatter.info("Inconsistent catalog length:")
            formatter.info(" claimed length: {}".format(self.claimed_length))
            formatter.info(" uids length: {}".format(self.uids_length))
            formatter.info(" paths length: {}".format(self.paths_length))
            formatter.info(" metadata length: {}".format(self.data_length))

        if self.is_index_data_healthy():
            formatter.info("Index data is healthy.")
        else:
            formatter.info(
                "Index data is unhealthy, found {} aberrations:".format(
                    len(self.aberrations)))
            for aberration in self.aberrations.values():
                aberration.write_result(formatter)
                formatter.info('')


class RemoveExtraRid(object):
    """Remove an extra rid from the catalog."""

    def __init__(self, catalog, aberration):
        self.catalog = catalog
        self.aberration = aberration

    def perform(self):
        rid = self.aberration.rid
        if len(self.aberration.paths) != 1:
            raise CantPerformSurgery(
                "Expected exactly one affected path, got: {}"
                .format(", ".join(self.aberration.paths)))

        path = list(self.aberration.paths)[0]
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
    """Performs surgery for an aberration, if possible.

    Surgeries are assigned based on symptoms. For each set of symptoms a
    surgical procedure can be registered. This decides if an aberration can
    be treated.
    """
    surgeries = {
        ('in_metadata_keys_not_in_uids_values',
         'in_paths_keys_not_in_uids_values',
         'uids_tuple_mismatches_paths_tuple',
         ): RemoveExtraRid
    }

    def __init__(self, catalog, aberration):
        self.catalog = catalog
        self.aberration = aberration

    def can_perform_surgery(self):
        return bool(self.get_surgery())

    def get_surgery(self):
        symptoms = self.aberration.catalog_symptoms
        return self.surgeries.get(symptoms, None)

    def perform_surgery(self):
        surgery = self.get_surgery()
        if not surgery:
            return None

        return surgery(self.catalog, self.aberration).perform()


class CatalogCheckup(object):
    """Run health checkup for a Products.ZCatalog.Catalog instance.

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

    def run(self):
        result = CheckupResult(self.catalog)

        paths = self.catalog.paths
        paths_values = set(self.catalog.paths.values())
        uids = self.catalog.uids
        uids_values = set(self.catalog.uids.values())
        data = self.catalog.data

        result.report_catalog_stats(
            len(self.catalog), len(uids), len(paths), len(data))

        for path, rid in uids.items():
            if rid not in paths:
                result.report_symptom(
                    'in_uids_values_not_in_paths_keys', rid, path=path)
            elif paths[rid] != path:
                result.report_symptom(
                    'paths_tuple_mismatches_uids_tuple', rid, path=path)

            if path not in paths_values:
                result.report_symptom(
                    'in_uids_keys_not_in_paths_values', rid, path=path)

            if rid not in data:
                result.report_symptom(
                    'in_uids_values_not_in_metadata_keys', rid, path=path)

        for rid, path in paths.items():
            if path not in uids:
                result.report_symptom(
                    'in_paths_values_not_in_uids_keys', rid, path=path)
            elif uids[path] != rid:
                result.report_symptom(
                    'uids_tuple_mismatches_paths_tuple', rid, path=path)

            if rid not in uids_values:
                result.report_symptom(
                    'in_paths_keys_not_in_uids_values', rid, path=path)

            if rid not in data:
                result.report_symptom(
                    'in_paths_keys_not_in_metadata_keys', rid, path=path)

        for rid in data:
            if rid not in paths:
                result.report_symptom(
                    'in_metadata_keys_not_in_paths_keys', rid)
            if rid not in uids_values:
                result.report_symptom(
                    'in_metadata_keys_not_in_uids_values', rid)

        return result
