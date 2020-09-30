.. contents:: Table of Contents


Introduction
============

The package ``ftw.catalogdoctor`` provides healthcheck to find
inconsistencies in ``portal_catalog`` and surgery to remove some of them. It
can be run via a ``zopectl.command``.


Healthcheck
===========

Lists inconsistencies detected in ``portal_catalog``. Finds inconsistencies by
inspecting the catalog's internal data structures. It currently uses ``paths``
(the rid-path mapping), ``uids`` (the path-rid mapping), the ``UID`` index and
catalog metadata to determine if the catalog is healthy or if there are
problems. Healtcheck is a read-only operation and won't modify the catalog.

It can be run as follows:

.. code:: sh

    $ bin/instance doctor healthcheck


Surgery
=======

Attempts to fix issues found by ``healthcheck``. Will do a healtchcheck before
surgery, then attempt surgery and finally do a post-surgery healthcheck.
Surgery is a write operation but changes are only committed to the database if
the post-surgery healtcheck yields no more health problems.
Currently the set of available surgery is limited to problems we have observed
in production.


It can be run as follows:

.. code:: sh

    $ bin/instance doctor surgery


There is also a `--dry-run` parameter that prevents committing changes.

.. code:: sh

    $ bin/instance doctor --dry-run surgery


Debugging
=========

If you need to debug/analyze issues that ``ftw.catalogdoctor`` cannot fix yet
have a look at the ``debug`` module. It provides useful functions to ``pprint``
or inspect catalog state.


Installation
============

- Add the package to your buildout configuration:

::

    [instance]
    eggs +=
        ...
        ftw.catalogdoctor


Compatibility
-------------

Plone 4.3.x
Plone 5.1.x


Development
===========

1. Fork this repo
2. Clone your fork
3. Shell: ``ln -s development.cfg buildout.cfg``
4. Shell: ``python bootstrap.py``
5. Shell: ``bin/buildout``

Run ``bin/test`` to test your changes.

Or start an instance by running ``bin/instance fg``.


Links
=====

- Github: https://github.com/4teamwork/ftw.catalogdoctor
- Issues: https://github.com/4teamwork/ftw.catalogdoctor/issues
- Pypi: http://pypi.python.org/pypi/ftw.catalogdoctor


Copyright
=========

This package is copyright by `4teamwork <http://www.4teamwork.ch/>`_.

``ftw.catalogdoctor`` is licensed under GNU General Public License, version 2.
