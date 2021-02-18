# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SauberRasterViewer
                                 A QGIS plugin
 View SAUBER project stations and corresponding data 
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2020-12-16
        copyright            : (C) 2020 by geomer GmbH
        email                : info@geomer.de
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SauberRasterViewer class from file SauberRasterViewer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .sauber_raster_viewer import SauberRasterViewer
    return SauberRasterViewer(iface)
