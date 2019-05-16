from __future__ import print_function
from ftw.catalogdoctor.healthcheck import CatalogHealthCheck
from ftw.catalogdoctor.surgery import CatalogDoctor
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
import argparse
import sys
import transaction


def discover_plone_site(app):
    for item_id, item in app.items():
        if IPloneSiteRoot.providedBy(item):
            return item_id
    return None


def load_site(app, path):
    if not path:
        print('ERROR: No Plone site found. Use --site or create a Plone site '
              'in the Zope app root.',
              file=sys.stderr)
        sys.exit(1)

    app = makerequest(app)
    site = app.unrestrictedTraverse(path)
    app.REQUEST.PARENTS = [site, app]
    setSite(site)

    return site


class ConsoleOutput(object):

    def info(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg, file=sys.stderr)


def healthcheck_command(portal_catalog):
    result = CatalogHealthCheck(catalog=portal_catalog).run()
    result.write_result(formatter=ConsoleOutput())
    return result


def surgery_command(portal_catalog):
    result = healthcheck_command(portal_catalog)

    formatter = ConsoleOutput()
    there_is_nothing_we_can_do = []

    for unhealthy_rid in result.get_unhealthy_rids():
        doctor = CatalogDoctor(result.catalog, unhealthy_rid)
        if doctor.can_perform_surgery():
            formatter.info(doctor.perform_surgery())
        else:
            there_is_nothing_we_can_do.append(unhealthy_rid)

    if there_is_nothing_we_can_do:
        formatter.info('The following unhealthy rids could not be fixed')
        for unhealthy_rid in there_is_nothing_we_can_do:
            unhealthy_rid.write_result(formatter)


def doctor_cmd(app, args):
    parser = argparse.ArgumentParser(
        description='Provide health check and fixes for portal_catalog.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # swallows instance command
    parser.add_argument('-c', help=argparse.SUPPRESS)

    parser.add_argument(
        '-s', '--site', dest='site',
        default=discover_plone_site(app),
        help='Path to the Plone site from which portal_catalog is used.')
    parser.add_argument(
        '-n', '--dry-run', dest='dryrun',
        default=False, action="store_true",
        help='Dryrun, do not commit changes')

    commands = parser.add_subparsers()
    healthcheck = commands.add_parser(
        'healthcheck',
        help='Run a health check for portal_catalog.')
    healthcheck.set_defaults(func=healthcheck_command)

    surgery = commands.add_parser(
        'surgery',
        help='Run a healthcheck and perform surgery for unhealthy rids in '
             'portal_catalog.')
    surgery.set_defaults(func=surgery_command)

    args = parser.parse_args(args)

    # if args.dryrun:
    transaction.doom()

    site = load_site(app, args.site)
    portal_catalog = getToolByName(site, 'portal_catalog')
    args.func(portal_catalog)

    # if not args.dryrun:
    #     transaction.commit()
