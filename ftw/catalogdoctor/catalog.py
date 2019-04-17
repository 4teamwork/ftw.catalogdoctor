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

    def write_result(self, formatter):
        path = self.path if self.path is not None else "--no path--"
        formatter.info("rid: {} ('{}')".format(
            self.rid, path))
        for symptom in self.catalog_symptoms:
            formatter.info('   - {}'.format(symptom))


class CheckupResult(object):
    """Provide health result for one catalog checkup run."""

    def __init__(self):
        self.aberrations = dict()
        self.claimed_length = None
        self.uids_length = None
        self.paths_length = None
        self.data_length = None

    def report_catalog_stats(self, claimed_length, uids_length, paths_length, data_length):
        self.claimed_length = claimed_length
        self.uids_length = uids_length
        self.paths_length = paths_length
        self.data_length = data_length

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
        result = CheckupResult()

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
