    # -*- coding: utf-8 -*-
"""
/***************************************************************************
 SauberStationViewer
                                 A QGIS plugin
 Select SAUBER project stations and access data 
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-12-16
        git sha              : $Format:%H$
        copyright            : (C) 2020 by geomer GmbH
        email                : info@geomer.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.utils import iface

from qgis.PyQt.QtWidgets import (
    QAction, 
    QInputDialog, 
    QLineEdit, 
    QLabel, 
    QVBoxLayout, 
    QWidget, 
    QTableWidgetItem
    )


from qgis.core import (
    Qgis,
    QgsProject, 
    QgsVectorLayer,
    QgsRectangle, 
    QgsPoint,
    QgsWkbTypes
)

from datetime import datetime
import requests
from requests.exceptions import HTTPError
import json

# Import data series plotter 
from .plotter import *
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .sauber_station_viewer_dialog import SauberStationViewerDialog
import os.path

# from mainwindow import Ui_MainWindow


# class AnotherWindow(QWidget):
#     """
#     This "window" is a QWidget. If it has no parent,
#     it will appear as a free-floating window.
#     """

#     def __init__(self):
#         super().__init__()
#         layout = QVBoxLayout()
#         self.label = QLabel("Graph")
#         layout.addWidget(self.label)
#         self.setLayout(layout)

#         for i in iface.mainWindow().findChildren(QtWidgets.QDockWidget):
#             if i.objectName() == 'Temporal Controller':
#                 i.setVisible(True)
#####################################################################################################

class SauberStationViewer:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        super().__init__

        self.station_dict = {}

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SauberStationViewer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SAUBER Station Viewer')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SauberStationViewer', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/sauber_station_viewer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'SAUBER Station viewer'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SAUBER Station Viewer'),
                action)
            self.iface.removeToolBarIcon(action)


    def checkLayerExists(self,layerSource):
        """
        Check if layer is already loaded to avoid duplicates.
        Expects Layer source since names can be changed.
        """

        layer_paths = []
        layer_paths = [layer.source() for layer in QgsProject.instance().mapLayers().values()]

        if layerSource in layer_paths:
            return
        else: 
            return 1


    def loadStationLayer(self,warning=True):
        """
        Load measuring station layer.
        TODO: SSL
        """

        wfs_url = "https://sauber-sdi.meggsimum.de/geoserver/station_data/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=station_data:fv_wfs"
        station_layer = QgsVectorLayer(wfs_url, "SAUBER Messstationen", "WFS")
        
        if self.checkLayerExists(wfs_url):
            if station_layer.isValid():
                QgsProject.instance().addMapLayer(station_layer)
            else: iface.messageBar().pushMessage("Error", "Layer mit Messstationen konnte nicht geladen werden", level=Qgis.Critical, duration=4)
            return
        elif warning==True: 
            iface.messageBar().pushMessage("Hinweis", "Messstationen-Layer bereits geladen", level=Qgis.Info, duration=4)
            return
        layer = QgsProject.instance().mapLayersByName("SAUBER Messstationen")[0]
        iface.setActiveLayer(layer)
        QgsProject.instance().layerTreeRoot().findLayer(layer).setItemVisibilityChecked(True)
        

    def loadStationData(self):
        """
        Get combination of station, component and time 
        Retrieve WFS answer
        Push to QTabelWidget
        """ 
        
        # Observe PostGIS date-time format 
        start_dt = self.dlg.start_date_btn.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        end_dt = self.dlg.end_date_btn.dateTime().toString("yyyy-MM-dd HH:mm:ss")

        # Check that end time is after and not equal start time   
        if (self.dlg.start_date_btn.dateTime().secsTo(self.dlg.end_date_btn.dateTime())) < 1:
            iface.messageBar().pushMessage("Error", "Abfragezeitraum ist null", level=Qgis.Critical, duration=4)
            return

        # Strip quotes from component 
        component_name = self.dlg.box_pollutant.currentText().replace('"', '')
        station_name = self.dlg.box_station.currentText()

        base_url = "https://sauber-sdi.meggsimum.de/geoserver/station_data/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=station_data%3Awfs_parameterized&outputFormat=application%2Fjson"
        request_url = base_url + "&viewparams=START_DATE:"+start_dt+";END_DATE:"+end_dt+";STATION_NAME:"+station_name+";COMPONENT_NAME:"+component_name

        try:
            request = requests.get(request_url, verify=False)#,auth)) # TODO: Enable auth, TODO: turn on cert verification
            station_data = request.text
        except HTTPError as http_err:
            print(f'HTTP error: {http_err}')
        except Exception as err:
            print(f'Error occurred: {err}')

        try: 
            self.data_dict = json.loads(station_data)
        except Exception as err:
            iface.messageBar().pushMessage("Error", "Fehler bei der Datenabfrage", level=Qgis.Critical, duration=4)
            print(f'Error occurred: {err}')
            return

        # Check if there is actually data in the request
        if len(self.data_dict["features"])>0:

            # Target data is a JSON within JSON, need to parse again
            series = json.loads(self.data_dict["features"][0]["properties"]["series"])

            # To load into table (str only), simplify from JSON Objects {date: , value:} to list
            # Cast time string to datetime to convert format later 
            data_series = []
            for i in series:
                # self.data.append((datetime.strptime(i["datetime"],"%Y-%m-%dT%H:%M:%S"),str(i["val"])))
                data_series.append((datetime.strptime(i["datetime"],"%Y-%m-%dT%H:%M:%S"),i["val"]))

            return data_series

        else:
            iface.messageBar().pushMessage("Error", "Keine Daten im Abfragezeitraum", level=Qgis.Critical, duration=4)



    def pushToTable(self):

        data = self.loadStationData()
        sd = [str(x[1]) for x in data]

        print(sd)

        # Construct table
        qTable = self.dlg.tableWidget
        qTable.clearContents()
        count_rows = len(data) 
        count_cols = len(data[0])
        qTable.setColumnCount(count_cols)
        qTable.setRowCount(count_rows)
        qTable.setHorizontalHeaderLabels([u'Zeitpunkt',u'Messwert'])

        # Load into table
        for row in range(count_rows):
            for column in range(count_cols):
                if isinstance(data[row][column], datetime):
                    qTable.setItem(row, column, QTableWidgetItem((data[row][column].strftime('%d.%m.%Y %H:%M'))))
                else:
                    qTable.setItem(row, column, QTableWidgetItem((data[row][column])))
        qTable.resizeColumnsToContents()

    

    def getStationLayerCombo(self):
        """
        Get all stations-component combinations from Geoserver WFS
        """
        pollutant_url = 'https://sauber-sdi.meggsimum.de/geoserver/station_data/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=station_data:fv_stations&outputFormat=application/json'

        try:
            station_pollutants = requests.get(pollutant_url, verify=False)#,auth)) # TODO: Enable auth, TODO: turn on cert verification
            station_response = station_pollutants.text
        except HTTPError as http_err:
            print(f'HTTP error: {http_err}')
        except Exception as err:
            print(f'Error occurred: {err}')

        # Parse reponse JSON and load into dict
        self.station_dict = json.loads(station_response)

        # Iterate over dict and fill stations list 
        stations = []
        for station in self.station_dict["features"]:
            stations.append(station["properties"]["station_name"]) if station["properties"]["station_name"] not in stations else stations

        # Sort for ordering in gui box
        stations.sort()

        # push to combobox
        self.dlg.box_station.clear()
        for i in stations:
            self.dlg.box_station.addItem(i)

        # Call function for first iteration
        self.getCurrStation()


    def getCurrStation(self):
        """ Listens to signal when station selection is changed in combobox """
        curr_station = self.dlg.box_station.currentText()
        self.filterPollutants(self.dlg.box_station.currentText())
        return curr_station


    def getCurrPollutant(self):
        # Listens to signal when pollutant selection is changed in combobox
        curr_pollutant = self.dlg.box_pollutant.currentText()
        print(curr_pollutant)
        return curr_pollutant


    def filterPollutants(self,station):
        """ Dict lookup: Find corresponding pollutants for selected station  """
        self.dlg.box_pollutant.clear()
        for i in self.station_dict["features"]:
            if i["properties"]["station_name"] == station:
                for j in i["properties"]["pollutants"][1:-1].split(","):
                    # Remove curly brackets and split for insert into second combo box
                    self.dlg.box_pollutant.addItem(j.replace('"',''))


    def zoomToStation(self):
        """Zoom / center raster layer"""
        self.loadStationLayer(warning=False)
        curr_station = self.getCurrStation()
        layer = iface.activeLayer()
        layer.removeSelection()
        feature=layer.selectByExpression("\"station_name\"='{0}'".format(curr_station))
        iface.actionZoomToSelected().trigger()

        #TODO: Use fixed bbox?
        # scale=1000
        # rect = QgsRectangle(float(stat_x)-scale,float(stat_y)-scale,float(stat_x)+scale,float(stat_y)+scale)
        # iface.mapCanvas().setExtent(rect)
        # iface.mapCanvas().refresh()


    def plot(self):
        """Show graph of data. Calls Plotter class"""
        self.loadStationData()
        plt_inst = Plotter()
        plt_inst.plot(self.dataseries)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = SauberStationViewerDialog()

            # Get initial station+pollutant combo to fill box
        self.getStationLayerCombo()

        # Clear combo boxes on new startup
        self.dlg.box_station.clear()
        self.dlg.box_pollutant.clear()

        # Listen to selection change signal, call function if changed
        self.dlg.box_station.activated.connect(self.getCurrStation)
        self.dlg.box_pollutant.activated.connect(self.getCurrPollutant)

        # Zoom to station btn
        self.dlg.zoom_to_station.clicked.connect(self.zoomToStation)

        # Load layer btn
        # self.dlg.load_layer_btn.clicked.connect(self.loadStationLayer)
        self.dlg.load_layer_btn.clicked.connect(lambda: self.loadStationLayer(True))

        # Get station data
        self.dlg.get_data_btn.clicked.connect(self.pushToTable)

        # Plot data
        self.dlg.plot_btn.clicked.connect(self.plot)

        self.dialogs = list()

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()