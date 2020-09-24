from ftw.builder.content import register_dx_content_builders
from ftw.builder.testing import BUILDER_LAYER
from ftw.builder.testing import functional_session_factory
from ftw.builder.testing import set_builder_session_factory
from ftw.testing.layer import COMPONENT_REGISTRY_ISOLATION
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2
from zope.configuration import xmlconfig
import logging
import sys


# Capture messages logged by certain indexes, we want to see these messages
# during test execution for better debugging/analysis.
# The loggers used by different indexes are not standardized, unfortunately.
LOG_TO_STDOUT_DURING_TESTRUN = {
    'BooleanIndex.UnIndex': logging.ERROR,
    'DateIndex': logging.ERROR,
    'Products.ZCatalog': logging.ERROR,
    'Zope.PathIndex': logging.DEBUG,
    'Zope.UnIndex': logging.ERROR,
}

loghandler = logging.StreamHandler(stream=sys.stdout)
loghandler.setLevel(logging.WARNING)
for name, level in LOG_TO_STDOUT_DURING_TESTRUN.items():
    logger = logging.getLogger(name)
    logger.addHandler(loghandler)
    logger.setLevel(level)


class CatalogdoctorLayer(PloneSandboxLayer):
    defaultBases = (COMPONENT_REGISTRY_ISOLATION, BUILDER_LAYER)

    def setUpZope(self, app, configurationContext):
        xmlconfig.string(
            '<configure xmlns="http://namespaces.zope.org/zope">'
            '  <include package="z3c.autoinclude" file="meta.zcml" />'
            '  <includePlugins package="plone" />'
            '  <includePluginsOverrides package="plone" />'
            '</configure>',
            context=configurationContext)

        # Prevent an error in layer setup by installing the product, error:
        # ValueError: Index of type DateRecurringIndex not found
        z2.installProduct(app, 'Products.DateRecurringIndex')

        z2.installProduct(app, 'ftw.catalogdoctor')

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'plone.app.contenttypes:default')
        register_dx_content_builders(force=True)


CATALOGDOCTOR_FIXTURE = CatalogdoctorLayer()
CATALOGDOCTOR_FUNCTIONAL = FunctionalTesting(
    bases=(CATALOGDOCTOR_FIXTURE,
           set_builder_session_factory(functional_session_factory)),
    name="ftw.catalogdoctor:functional")
