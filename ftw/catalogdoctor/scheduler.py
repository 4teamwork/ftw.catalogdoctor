from ftw.catalogdoctor.surgery import CatalogDoctor
from plone import api


class SurgeryScheduler(object):
    """Performs surgeries based on a healthcheck result."""

    def __init__(self, healtcheck, catalog=None):
        self.healtcheck = healtcheck
        self.portal_catalog = catalog or api.portal.get_tool('portal_catalog')
        self.catalog = self.portal_catalog._catalog
        self.doctors = [
            CatalogDoctor(self.catalog, unhealthy_rid)
            for unhealthy_rid in self.healtcheck.get_unhealthy_rids()
        ]

    def perform_surgeries(self):
        for doctor in self.doctors:
            doctor.perform_surgery()

        for doctor in self.doctors:
            doctor.perform_post_op()

    def is_successful(self):
        return all(doctor.can_perform_surgery() for doctor in self.doctors)

    def write_result(self, formatter):
        there_is_nothing_we_can_do = []
        for doctor in self.doctors:
            if doctor.can_perform_surgery():
                doctor.write_result(formatter)
                formatter.info('')
            else:
                there_is_nothing_we_can_do.append(doctor.unhealthy_rid)

        if there_is_nothing_we_can_do:
            formatter.info('The following unhealthy rids could not be fixed:')
            for unhealthy_rid in there_is_nothing_we_can_do:
                unhealthy_rid.write_result(formatter)
                formatter.info('')

            formatter.info('Not all health problems could be fixed, aborting.')
