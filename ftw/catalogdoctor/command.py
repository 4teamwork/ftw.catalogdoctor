from __future__ import print_function
from ftw.catalogdoctor.compat import processQueue
from ftw.catalogdoctor.healthcheck import CatalogHealthCheck
from ftw.catalogdoctor.scheduler import SurgeryScheduler
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


def healthcheck_command(portal_catalog, args, formatter):
    transaction.doom()  # extra paranoia, prevent erroneous commit

    return _run_healthcheck(portal_catalog, formatter)


def _run_healthcheck(portal_catalog, formatter):
    result = CatalogHealthCheck(catalog=portal_catalog).run()
    result.write_result(formatter)
    return result


def surgery_command(portal_catalog, args, formatter):
    if args.dryrun:
        formatter.info('Performing dryrun!')
        formatter.info('')
        transaction.doom()

    result = _run_healthcheck(portal_catalog, formatter)
    if result.is_healthy():
        transaction.doom()  # extra paranoia, prevent erroneous commit
        formatter.info('Catalog is healthy, no surgery is needed.')
        return

    formatter.info('Performing surgery:')
    scheduler = SurgeryScheduler(result, catalog=portal_catalog)
    scheduler.perform_surgeries()
    scheduler.write_result(formatter)
    if not scheduler.is_successful():
        return

    processQueue()

    formatter.info('Performing post-surgery healthcheck:')
    post_result = _run_healthcheck(portal_catalog, formatter)
    if not post_result.is_healthy():
        transaction.doom()   # extra paranoia, prevent erroneous commit
        formatter.info('Not all health problems could be fixed, aborting.')
        return

    if args.dryrun:
        formatter.info('Surgery would have been successful, but was aborted '
                       'due to dryrun!')
    else:
        transaction.commit()
        formatter.info('Surgery was successful, known health problems could '
                       'be fixed!')


def _setup_parser(app):
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
        help='Dryrun, do not commit changes. Only relevant for surgery.')

    commands = parser.add_subparsers(dest='command')
    healthcheck = commands.add_parser(
        'healthcheck',
        help='Run a health check for portal_catalog.')
    healthcheck.set_defaults(func=healthcheck_command)

    surgery = commands.add_parser(
        'surgery',
        help='Run a healthcheck and perform surgery for unhealthy rids in '
             'portal_catalog.')
    surgery.set_defaults(func=surgery_command)
    return parser


def _parse(parser, args):
    return parser.parse_args(args)


def _run(parsed_args, app, formatter):
    site = load_site(app, parsed_args.site)
    portal_catalog = getToolByName(site, 'portal_catalog')

    return parsed_args.func(portal_catalog, parsed_args, formatter=formatter)


def doctor_cmd(app, args, formatter=None):
    parser = _setup_parser(app)
    parsed_args = _parse(parser, args)
    _run(parsed_args, app, formatter or ConsoleOutput())
