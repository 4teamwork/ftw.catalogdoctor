from setuptools import setup, find_packages
import os

version = '1.2.0'

tests_require = [
    'ftw.builder',
    'ftw.testbrowser',
    'ftw.testing',
    'plone.app.contenttypes',
    'plone.app.testing',
    'plone.testing',
    'pytz',
    'zope.configuration',
]

extras_require = {
    'tests': tests_require,
}


setup(
    name='ftw.catalogdoctor',
    version=version,
    description='ftw.catalogdoctor',
    long_description=open('README.rst').read() + '\n' + open(
        os.path.join('docs', 'HISTORY.txt')).read(),

    # Get more strings from
    # http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Framework :: Plone',
        'Framework :: Plone :: 4.3',
        'Framework :: Plone :: 5.1',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    keywords='ftw catalogdoctor',
    author='4teamwork AG',
    author_email='mailto:info@4teamwork.ch',
    url='https://github.com/4teamwork/ftw.catalogdoctor',
    license='GPL2',

    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['ftw'],
    include_package_data=True,
    zip_safe=False,

    install_requires=[
        'ftw.upgrade',
        'Plone',
        'plone.api',
        'setuptools',
    ],

    tests_require=tests_require,
    extras_require=extras_require,

    entry_points="""
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = plone

    [zopectl.command]
    doctor = ftw.catalogdoctor.command:doctor_cmd
    """,
)
