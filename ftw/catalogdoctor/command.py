from __future__ import print_function
from ftw.catalogdoctor.catalog import CatalogCheckup
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
import argparse
import sys


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


def checkup_command(site, args):
    result = CatalogCheckup(catalog=site.portal_catalog).run()
    result.write_result(formatter=ConsoleOutput())


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

    commands = parser.add_subparsers()
    command = commands.add_parser(
        'checkup',
        help='Run a checkup for portal_catalog.')
    command.set_defaults(func=checkup_command)

    args = parser.parse_args(args)
    site = load_site(app, args.site)
    args.func(site, args)
