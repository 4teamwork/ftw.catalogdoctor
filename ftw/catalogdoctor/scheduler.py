from ftw.catalogdoctor.surgery import CatalogDoctor
from plone import api


class SurgeryScheduler(object):
    """Performs surgeries based on a healthcheck result."""

    def __init__(self, healtcheck, catalog=None):
        self.healtcheck = healtcheck
        self.portal_catalog = catalog or api.portal.get_tool('portal_catalog')
        self.catalog = self.portal_catalog._catalog

    def perform_surgeries(self):
        there_is_nothing_we_can_do = []
        surgeries = []
        for unhealthy_rid in self.healtcheck.get_unhealthy_rids():
            doctor = CatalogDoctor(self.catalog, unhealthy_rid)
            if doctor.can_perform_surgery():
                surgery = doctor.perform_surgery()
                surgeries.append(surgery)
            else:
                there_is_nothing_we_can_do.append(unhealthy_rid)

        return there_is_nothing_we_can_do, surgeries
