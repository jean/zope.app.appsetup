##############################################################################
#
# Copyright (c) 2002, 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap code.

This module contains code to bootstrap a Zope3 instance.  For example
it makes sure a root folder exists and creates one if necessary.

$Id$
"""
__docformat__ = 'restructuredtext'
from transaction import get_transaction

import zope.event

from zope.app.component.interfaces import ISite
from zope.app.component import site
from zope.app.container.interfaces import INameChooser
from zope.app.folder import rootFolder
from zope.app.publication.zopepublication import ZopePublication
from zope.app.traversing.api import traverse
from zope.app.appsetup import interfaces

def ensureObject(root_folder, object_name, object_type, object_factory):
    """Check that there's a basic object in the site
    manager. If not, add one.

    Return the name abdded, if we added an object, otherwise None.
    """
    package = getSiteManagerDefault(root_folder)
    valid_objects = [ name
                      for name in package
                      if object_type.providedBy(package[name]) ]
    if valid_objects:
        return None
    name = object_name
    obj = object_factory()
    package[name] = obj
    return name

def ensureUtility(root_folder, interface, utility_type,
                  utility_factory, name='', **kw):
    """Add a utility to the top site manager

    Returns the name added or ``None`` if nothing was added.
    """
    sm = root_folder.getSiteManager()
    utils = [reg for reg in sm.utilities.registrations()
             if reg.provided.isOrExtends(interface)]
    if len(utils) == 0:
        return addConfigureUtility(
            root_folder, interface, utility_type, utility_factory,
            name, **kw
            )
    else:
        return None

def addConfigureUtility(
        root_folder, interface, utility_type, utility_factory, name='', **kw):
    """Add and configure a utility to the root folder."""
    utility_name = addUtility(root_folder, utility_type, utility_factory, **kw)
    configureUtility(root_folder, interface, utility_type, name, utility_name)
    return name

def addUtility(root_folder, utility_type, utility_factory, **kw):
    """ Add a Utility to the root folder's site manager.

    The utility is added to the default package and activated.
    """
    package = getSiteManagerDefault(root_folder)
    chooser = INameChooser(package)
    utility = utility_factory()
    name = chooser.chooseName(utility_type, utility)
    package[name] = utility
    # Set additional attributes on the utility
    for k, v in kw.iteritems():
        setattr(utility, k, v)
    return name

def configureUtility(
        root_folder, interface, utility_type, name, folder_name,
        initial_status=u'Active'):
    """Configure a utility in the root folder."""
    package = getSiteManagerDefault(root_folder)
    registration_manager = package.registrationManager
    reg = site.UtilityRegistration(name, interface, package[folder_name])
    key = registration_manager.addRegistration(reg)
    reg.status = initial_status

def getSiteManagerDefault(root_folder):
    package_name = '/++etc++site/default'
    package = traverse(root_folder, package_name)
    return package

def getInformationFromEvent(event):
    """ Extracts information from the event

    Return a tuple containing

      - db
      - connection open from the db
      - root connection object
      - the root_folder object
    """
    db = event.database
    connection = db.open()
    root = connection.root()
    root_folder = root.get(ZopePublication.root_name, None)
    return db, connection, root, root_folder


######################################################################
######################################################################

def bootStrapSubscriber(event):
    """The actual subscriber to the bootstrap IDataBaseOpenedEvent

    Boostrap a Zope3 instance given a database object This first checks if the
    root folder exists and has a site manager.  If it exists, nothing else
    is changed.  If no root folder exists, one is added.
    """

    db, connection, root, root_folder = getInformationFromEvent(event)
    root_created = False

    if root_folder is None:
        root_created = True
        # ugh... we depend on the root folder implementation
        root_folder = rootFolder()
        root[ZopePublication.root_name] = root_folder
        if not ISite.providedBy(root_folder):
            site_manager = site.LocalSiteManager(root_folder)
            root_folder.setSiteManager(site_manager)

        get_transaction().commit()

    connection.close()

    zope.event.notify(interfaces.DatabaseOpenedWithRoot(db))

########################################################################
########################################################################
