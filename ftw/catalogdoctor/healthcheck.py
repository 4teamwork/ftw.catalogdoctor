from plone import api


class CatalogHealthCheck(object):
    """Run health check for a Products.ZCatalog.Catalog instance.

    Validates that the catalogs uid and rid mapping and metadata is consistent.
    This means that:
    - the mappings have the same length
    - the mappings are consistent, so every item is in the reverse mapping
    - for every item there is also an entry in the catalog metadata

    The health check does not validate indices and index data yet.
    """
    def __init__(self, catalog=None):
        self.portal_catalog = catalog or api.portal.get_tool('portal_catalog')
        self.catalog = self.portal_catalog._catalog

    def run(self):
        result = HealthCheckResult(self.catalog)

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


class UnhealthyRid(object):
    """Represents a rid which is considered unhealthy.

    A rid becomes unhealthy if the health check finds one or more issues
    with that rid. An `UnhealthyRid` instance groups all issues/symptoms found
    for one rid.

    """
    def __init__(self, rid):
        self.rid = rid
        self._paths = set()
        self._catalog_symptoms = set()

    def attach_path(self, path):
        self._paths.add(path)

    def report_catalog_symptom(self, name):
        """Report a symptom found in the the catalog."""

        self._catalog_symptoms.add(name)

    @property
    def catalog_symptoms(self):
        return tuple(sorted(self._catalog_symptoms))

    @property
    def paths(self):
        return tuple(sorted(self._paths))

    def write_result(self, formatter):
        if self.paths:
            paths = ", ".join("'{}'".format(p) for p in self.paths)
        else:
            paths = "--no path--"
        formatter.info("rid: {} ({})".format(self.rid, paths))
        for symptom in self.catalog_symptoms:
            formatter.info('\t- {}'.format(symptom))


class HealthCheckResult(object):
    """Provide health check result for one catalog health check run."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.unhealthy_rids = dict()
        self.claimed_length = None
        self.uids_length = None
        self.paths_length = None
        self.data_length = None

    def get_unhealthy_rids(self):
        return self.unhealthy_rids.values()

    def report_catalog_stats(self, claimed_length, uids_length, paths_length, data_length):
        self.claimed_length = claimed_length
        self.uids_length = uids_length
        self.paths_length = paths_length
        self.data_length = data_length

    def _make_unhealthy_rid(self, rid, path=None):
        if rid not in self.unhealthy_rids:
            self.unhealthy_rids[rid] = UnhealthyRid(rid)

        unhealthy_rid = self.unhealthy_rids[rid]
        if path:
            unhealthy_rid.attach_path(path)
        return unhealthy_rid

    def report_symptom(self, name, rid, path=None):
        unhealthy_rid = self._make_unhealthy_rid(rid, path=path)
        unhealthy_rid.report_catalog_symptom(name)
        return unhealthy_rid

    def get_symptoms(self, rid):
        return self.unhealthy_rids[rid].catalog_symptoms

    def is_healthy(self):
        """Return whether the catalog is healthy according to this result."""

        return self.is_index_data_healthy() and self.is_length_healthy()

    def is_index_data_healthy(self):
        return not self.unhealthy_rids

    def is_length_healthy(self):
        return (
            self.claimed_length
            == self.uids_length
            == self.paths_length
            == self.data_length
        )

    def write_result(self, formatter):
        """Log result to logger."""

        formatter.info("Catalog health check report:")

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
                "Index data is unhealthy, found {} unhealthy rids:".format(
                    len(self.unhealthy_rids)))
            for unhealthy_rid in self.unhealthy_rids.values():
                unhealthy_rid.write_result(formatter)
                formatter.info('')
