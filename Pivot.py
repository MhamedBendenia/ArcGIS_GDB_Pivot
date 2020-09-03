"""
    Tool : Pivot, Source Name : Pivot.py, Author: M'hamed Bendenia.
"""

from arcgis.features import GeoAccessor
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import arcpy
import os
import wx
import pathlib
import math


class Pivot(wx.Frame):
    """ A powerful hypercube rotation tool for ArcGIS Pro. """

    workspace = None  #: Default gdb path
    workfolder = None  #: Default gdb folder path
    aprx = arcpy.mp.ArcGISProject("CURRENT")  #: Current project
    active_map = None  #: Current map
    data_warehouse = {}  #: Data Warehouse
    fact_table = None  #: Fact table
    sizer = wx.GridBagSizer(0, 0)  #: Layer sizer
    panel = None  #: Pivot panel
    axes = None  #: Pivot axes
    bmp = None  #: Bitmap image axes
    xChoice = yChoice = zChoice = None  #: Dimension choise
    feature_class = None  #: ArcGIS Pro feature class
    x = y = z = None  #: Bitmap axe

    # Define default GDB if parameter is Null
    if len(arcpy.GetParameterAsText(0)) == 0:
        workspace = arcpy.env.workspace
        workfolder = os.path.dirname(workspace)
    else:
        workspace = arcpy.GetParameter(0)
        arcpy.env.workspace = workspace
        workfolder = os.path.dirname(arcpy.env.workspace)

    # Define current map if parameter is Null
    if len(arcpy.GetParameterAsText(1)) == 0:
        active_map = aprx.listMaps()[0]
    else:
        active_map = aprx.listMaps(arcpy.GetParameter(1))[0]

    # Setup reference Scale
    active_map.referenceScale = 59467124.861567564

    # Putting all layers in a dict
    lyr_dict = {lyr.name.lower(): lyr for lyr in active_map.listLayers()}

    def __init__(self, parent, title):
        """
        Initialise the Pivot interface

        :param parent: The main Window
        :param title: Window title
        """
        super(Pivot, self).__init__(parent, title=title, size=wx.Size(410, 250),
                                    style=wx.STAY_ON_TOP ^ wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):
        """
        Display the user interface and load data.
        """
        self.panel = wx.Panel(self)
        self.local = wx.Locale(wx.LANGUAGE_DEFAULT)

        # Axes image
        self.bmp = wx.Bitmap(str(pathlib.Path().absolute().joinpath(r"Scripts\Axes.png")), wx.BITMAP_TYPE_PNG)
        self.axes = wx.StaticBitmap(self.panel, wx.ID_ANY, self.bmp, wx.DefaultPosition, (120, 120), 0)
        self.axes.Bind(wx.EVT_LEFT_DOWN, self.onAxesClick)
        self.sizer.Add(self.axes, pos=(1, 1), flag=wx.ALL, border=5)

        # The lists of choices
        self.xChoice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, size=wx.Size(120, 25), style=0)
        self.xChoice.Bind(wx.EVT_CHOICE, self.onXChoiceClick)
        self.sizer.Add(self.xChoice, pos=(2, 2), flag=wx.ALL, border=5)

        self.yChoice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, size=wx.Size(120, 25), style=0)
        self.yChoice.Bind(wx.EVT_CHOICE, self.onYChoiceClick)
        self.sizer.Add(self.yChoice, pos=(0, 1), flag=wx.ALL, border=5)

        self.zChoice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, size=wx.Size(120, 25), style=0)
        self.zChoice.Bind(wx.EVT_CHOICE, self.onZChoiceClick)
        self.sizer.Add(self.zChoice, pos=(2, 0), flag=wx.ALL, border=5)

        # Filling the DW and the lists by feature classes
        for fc in arcpy.ListFeatureClasses():
            try:
                self.data_warehouse[fc.title().lower()] = pd.DataFrame.spatial.from_featureclass(fc)
                self.xChoice.Append(fc.title())
                self.yChoice.Append(fc.title())
                self.zChoice.Append(fc.title())
            except Exception as e:
                arcpy.AddError(str(e))

        # Filling the DW and the lists by tables
        for tb in arcpy.ListTables():
            try:
                self.data_warehouse[tb.title().lower()] = pd.DataFrame.spatial.from_table(tb)
                self.xChoice.Append(tb.title())
                self.yChoice.Append(tb.title())
                self.zChoice.Append(tb.title())
            except Exception as e:
                arcpy.AddError(str(e))
        self.panel.SetSizerAndFit(self.sizer)

    def onAxesClick(self, event):
        """
        Bitmap click event listner

        :param event: The mouse click event
        """
        x, y = event.GetPosition()
        if 91 < x < 106 and 88 < y < 104:
            self.bmp = wx.Bitmap(str(pathlib.Path().absolute().joinpath(r"Scripts\X.png")), wx.BITMAP_TYPE_PNG)
            self.axes.SetBitmap(self.bmp)
            self.panel.Layout()

            temp = self.zChoice.GetSelection()
            self.zChoice.SetSelection(self.yChoice.GetSelection())
            self.yChoice.SetSelection(temp)
            self.pivotRun()
            return
        elif 51 < x < 67 and 14 < y < 30:
            self.bmp = wx.Bitmap(str(pathlib.Path().absolute().joinpath(r"Scripts\Y.png")), wx.BITMAP_TYPE_PNG)
            self.axes.SetBitmap(self.bmp)
            self.panel.Layout()

            temp = self.xChoice.GetSelection()
            self.xChoice.SetSelection(self.zChoice.GetSelection())
            self.zChoice.SetSelection(temp)
            self.pivotRun()
            return
        elif 13 < x < 27 and 88 < y < 104:
            self.bmp = wx.Bitmap(str(pathlib.Path().absolute().joinpath(r"Scripts\Z.png")), wx.BITMAP_TYPE_PNG)
            self.axes.SetBitmap(self.bmp)
            self.panel.Layout()

            temp = self.xChoice.GetSelection()
            self.xChoice.SetSelection(self.yChoice.GetSelection())
            self.yChoice.SetSelection(temp)
            self.pivotRun()
            return
        return

    def onXChoiceClick(self, event):
        """
        X combobox click event listner

        :param event: The mouse click event
        """
        if self.yChoice.GetSelection() == wx.NOT_FOUND or self.zChoice.GetSelection() == wx.NOT_FOUND:
            return
        else:
            self.pivotRun()

    def onYChoiceClick(self, event):
        """
        Y combobox click event listner

        :param event: The mouse click event
        """
        if self.zChoice.GetSelection() == wx.NOT_FOUND or self.zChoice.GetSelection() == wx.NOT_FOUND:
            return
        else:
            self.pivotRun()

    def onZChoiceClick(self, event):
        """
        Z combobox click event listner

        :param event: The mouse click event
        """
        if self.yChoice.GetSelection() == wx.NOT_FOUND or self.xChoice.GetSelection() == wx.NOT_FOUND:
            return
        else:
            self.pivotRun()

    def pivotRun(self):
        """
        Start the Pivot operation
        """
        self.reset_lyrs()

        arcpy.AddMessage("---------------------")
        if self.xChoice.GetString(self.xChoice.GetSelection()).lower() == "date_world_cases":
            if self.yChoice.GetString(self.yChoice.GetSelection()).lower() == "covid_cases":
                arcpy.AddMessage("3")

                """Z with Z.fields[0] as label"""
                self.makeLabel(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                               field_name="Country_Re")

                """Z symbolized with Z.fields[3]"""
                self.make_class_breaks_symb(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())

                """Plot X(time) Y(point)"""
                self.stackPlot(data_name="covid_cases")

                self.hide(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())
                self.hide(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())

            else:
                arcpy.AddMessage("6")

                """Time cursor X"""
                self.setTimeCursor(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower(),
                                   time_field="Date")

                """Y symbolized with Y.fields[3]"""
                self.make_class_breaks_symb(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())

                """Plot X(states) Y(count_accidents)"""
                self.graphPlot(data_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())

                self.hide(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())

        elif self.xChoice.GetString(self.xChoice.GetSelection()).lower() == "covid_cases":
            if self.yChoice.GetString(self.yChoice.GetSelection()).lower() == "date_world_cases":
                arcpy.AddMessage("4")

                self.makeLabel(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                               field_name="Country_Re")

                self.hide(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())
                self.hide(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())

                self.linePlot(data_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())
            else:
                arcpy.AddMessage("2")

                self.make_simple_symb(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())
                self.setTimeCursor(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                                   time_field="Date")
                self.make_point_class_breaks_symb(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())
                self.setTimeCursor(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower(),
                                   time_field="Date")

        elif self.xChoice.GetString(self.xChoice.GetSelection()).lower() == "world_cases":
            if self.yChoice.GetString(self.yChoice.GetSelection()).lower() == "date_world_cases":
                arcpy.AddMessage("5")

                self.make_class_breaks_symb(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())
                self.rateLinePlot(data_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())

                self.hide(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())
            else:
                arcpy.AddMessage("1")

                self.make_time_related_symb(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                                            time_field="Date")

                self.hide(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())
        else:
            arcpy.AddWarning("This position is not supported.")
        return

    def rateLinePlot(self, data_name):
        """
        Rate plot

        :param data_name: Time dimension name
        """
        df_temp = self.data_warehouse[data_name].groupby("Date")["Confirmed", "Deaths", "Recovred"].max().reset_index()

        # Agregate Date
        df_temp['Date'] = pd.to_datetime(df_temp['Date'])
        df_temp = df_temp.groupby(pd.Grouper(key='Date', freq='W-MON'))["Confirmed",
                                                                        "Deaths",
                                                                        "Recovred"].max().reset_index()

        fig, ax = plt.subplots(figsize=(20, 5))

        plt.grid()
        ax.plot(df_temp.Date.values, df_temp.Deaths.values / df_temp.Confirmed.values, 'r--', marker="o",
                label="Deaths")
        ax.plot(df_temp.Date.values, df_temp.Recovred.values / df_temp.Confirmed.values, 'g--', marker="o",
                label="Recovred")

        ax.legend(loc=2)
        plt.title("Deaths and Recovred rates.")
        ax.set_yticklabels(['{:.1f}%'.format(x * 100) for x in ax.get_yticks()])
        plt.xticks(rotation=70)
        plt.yticks(rotation=60)
        plt.tight_layout()
        plt.show()

    def linePlot(self, data_name):
        """
        Line plot

        :param data_name: The dimension name
        """
        df_temp = self.data_warehouse[data_name].groupby("Date")["Confirmed", "Deaths", "Recovred"].max().reset_index()

        # Agregate Date
        df_temp['Date'] = pd.to_datetime(df_temp['Date'])
        df_temp = df_temp.groupby(pd.Grouper(key='Date', freq='W-MON'))["Confirmed",
                                                                        "Deaths",
                                                                        "Recovred"].max().reset_index()

        fig, ax = plt.subplots(figsize=(20, 5))
        plt.grid()
        ax.plot(df_temp.Date.values, df_temp.Deaths.values, 'r--', label="Deaths")
        ax.plot(df_temp.Date.values, df_temp.Recovred.values, 'g--', label="Recovred")
        ax.plot(df_temp.Date.values, df_temp.Confirmed.values, 'y--', label="Confirmed")

        ax.legend(loc=2)
        plt.title("Confirmed, Deaths and Recovred cases developement by Date.")
        plt.xticks(rotation=70)
        plt.yticks(rotation=60)
        plt.tight_layout()
        plt.show()

    def graphPlot(self, data_name):
        """
        Bar plot

        :param data_name: The dimension name
        """
        try:
            df_temp = self.data_warehouse[data_name].groupby("Country_Re")[["Confirmed",
                                                                            "Deaths",
                                                                            "Recovred"]].max().reset_index()
            df_temp.drop(df_temp[(df_temp.Confirmed == 0) & (df_temp.Recovred == 0) & (df_temp.Deaths == 0)].index,
                         inplace=True)
            data = pd.DataFrame.spatial.from_featureclass("covid_cases")
            df_temp = data.groupby("Country_Re")[["Confirmed", "Deaths", "Recovred"]].max().reset_index()
            df_temp.drop(df_temp[(df_temp.Confirmed == 0) & (df_temp.Recovred == 0) & (df_temp.Deaths == 0)].index,
                         inplace=True)

            n = math.ceil(df_temp.Country_Re.count() / 2)
            ind = np.arange(df_temp.Country_Re.count())[:n]

            f, (ax1, ax2) = plt.subplots(nrows=2, figsize=(20, 10), dpi=70)

            p1 = ax1.bar(ind - 0.25, df_temp.Confirmed.head(n), 0.25, color=(0.95, 0.62, 0.07, 1), picker=6)
            p2 = ax1.bar(ind, df_temp.Recovred.head(n), 0.25, color=(0.12, 0.52, 0.29, 1), picker=6)
            p3 = ax1.bar(ind + 0.25, df_temp.Deaths.head(n), 0.25, color=(1, 0, 0, 1), picker=6)

            p4 = ax2.bar(ind - 0.25, df_temp.Confirmed.tail(n), 0.25, color=(0.95, 0.62, 0.07, 1), picker=6)
            p5 = ax2.bar(ind, df_temp.Recovred.tail(n), 0.25, color=(0.12, 0.52, 0.29, 1), picker=6)
            p6 = ax2.bar(ind + 0.25, df_temp.Deaths.tail(n), 0.25, color=(1, 0, 0, 1), picker=6)

            def on_pick(event):
                rect = event.artist
                height = rect.get_height()
                try:
                    ann = ax1.annotate('{}'.format(height),
                                       xy=(rect.get_x() + rect.get_width() / 2, height),
                                       xytext=(0, 3),  # 3 points vertical offset
                                       textcoords="offset points",
                                       ha='center', va='bottom')

                    ann2 = ax2.annotate('{}'.format(height),
                                        xy=(rect.get_x() + rect.get_width() / 2, height),
                                        xytext=(0, 3),  # 3 points vertical offset
                                        textcoords="offset points",
                                        ha='center', va='bottom')

                    plt.pause(1)
                    ann.remove()
                    ann2.remove()
                    f.canvas.draw()
                except Exception as e:
                    print(str(e))

            f.canvas.mpl_connect('pick_event', on_pick)

            plt.sca(ax1)
            ax1.set_title('Confirmed, Recovred and Deaths numbers by Country_Re.')
            plt.xticks(ind, df_temp.Country_Re.head(n), rotation=90)
            ax1.set_yscale('symlog')
            ax1.legend((p1[0], p2[0], p3[0]), ('Confirmed', 'Recovred', 'Deaths'))
            ax1.margins(x=0.001)
            plt.tick_params(axis="x", width=10)
            plt.tight_layout()

            plt.sca(ax2)
            ax2.set_title('Confirmed, Recovred and Deaths numbers by Country_Re.')
            plt.xticks(ind, df_temp.Country_Re.tail(n), rotation=90)
            ax2.set_yscale('symlog')
            ax2.legend((p4[0], p5[0], p6[0]), ('Confirmed', 'Recovred', 'Deaths'))
            ax2.margins(x=0.001)

            plt.tick_params(axis="x", width=10)
            plt.tight_layout()

            plt.show()
        except Exception as e:
            arcpy.AddError(str(e))

    def stackPlot(self, data_name):
        """
        Stack plot

        :param data_name: The dimension name
        """
        df_temp = self.data_warehouse[data_name].groupby("Date")[
            "Confirmed", "Deaths", "Recovred"].max().reset_index()
        # Agregate Date
        df_temp['Date'] = pd.to_datetime(df_temp['Date'])
        df_temp = df_temp.groupby(pd.Grouper(key='Date', freq='W-MON'))[
            "Confirmed", "Deaths", "Recovred"].max().reset_index()

        fig, ax = plt.subplots(figsize=(20, 5))
        plt.grid()
        ax.stackplot(df_temp.Date.values, df_temp.Deaths.values, df_temp.Recovred.values, df_temp.Confirmed.values,
                     labels=["Deaths", "Recovred", "Confirmed"],
                     colors=[(1, 0, 0, 1), (0.12, 0.52, 0.29, 1), (0.95, 0.62, 0.07, 1)])
        ax.legend(loc=2)
        plt.title("Confirmed, Deaths and Recovred cases stack by Date.")
        plt.xticks(rotation=70)
        plt.tight_layout()
        plt.show()

    def makeLabel(self, lyr_name, field_name):
        """
        Setup lauer labels

        :param lyr_name: The layer name
        :param field_name: The field's name we want to label with
        """
        lyr = self.lyr_dict[lyr_name]
        definition = lyr.getDefinition('V2')
        definition.visibility = True
        definition.labelClasses[0] = {
            "type": "CIMLabelClass",
            "expression": "$feature."+field_name,
            "expressionEngine": "Arcade",
            "featuresToLabel": "AllVisibleFeatures",
            "maplexLabelPlacementProperties": {
                "type": "CIMMaplexLabelPlacementProperties",
                "featureType": "Polygon",
                "avoidPolygonHoles": True,
                "canOverrunFeature": True,
                "canPlaceLabelOutsidePolygon": True,
                "canRemoveOverlappingLabel": True,
                "canStackLabel": True,
                "connectionType": "Unambiguous",
                "constrainOffset": "NoConstraint",
                "contourAlignmentType": "Page",
                "contourLadderType": "Straight",
                "contourMaximumAngle": 90,
                "enableConnection": True,
                "featureWeight": 0,
                "fontHeightReductionLimit": 4,
                "fontHeightReductionStep": 0.5,
                "fontWidthReductionLimit": 90,
                "fontWidthReductionStep": 5,
                "graticuleAlignmentType": "Straight",
                "keyNumberGroupName": "Default",
                "labelBuffer": 15,
                "labelLargestPolygon": True,
                "labelPriority": -1,
                "labelStackingProperties": {
                    "type": "CIMMaplexLabelStackingProperties",
                    "stackAlignment": "ChooseBest",
                    "maximumNumberOfLines": 3,
                    "minimumNumberOfCharsPerLine": 3,
                    "maximumNumberOfCharsPerLine": 24,
                    "separators": [
                        {
                            "type": "CIMMaplexStackingSeparator",
                            "separator": " ",
                            "splitAfter": True
                        },
                        {
                            "type": "CIMMaplexStackingSeparator",
                            "separator": ",",
                            "visible": True,
                            "splitAfter": True
                        }
                    ]
                },
                "lineFeatureType": "General",
                "linePlacementMethod": "OffsetCurvedFromLine",
                "maximumLabelOverrun": 80,
                "maximumLabelOverrunUnit": "Point",
                "minimumFeatureSizeUnit": "Map",
                "multiPartOption": "OneLabelPerPart",
                "offsetAlongLineProperties": {
                    "type": "CIMMaplexOffsetAlongLineProperties",
                    "placementMethod": "BestPositionAlongLine",
                    "labelAnchorPoint": "CenterOfLabel",
                    "distanceUnit": "Percentage",
                    "useLineDirection": True
                },
                "pointExternalZonePriorities": {
                    "type": "CIMMaplexExternalZonePriorities",
                    "aboveLeft": 4,
                    "aboveCenter": 2,
                    "aboveRight": 1,
                    "centerRight": 3,
                    "belowRight": 5,
                    "belowCenter": 7,
                    "belowLeft": 8,
                    "centerLeft": 6
                },
                "pointPlacementMethod": "AroundPoint",
                "polygonAnchorPointType": "GeometricCenter",
                "polygonBoundaryWeight": 0,
                "polygonExternalZones": {
                    "type": "CIMMaplexExternalZonePriorities",
                    "aboveLeft": 4,
                    "aboveCenter": 2,
                    "aboveRight": 1,
                    "centerRight": 3,
                    "belowRight": 5,
                    "belowCenter": 7,
                    "belowLeft": 8,
                    "centerLeft": 6
                },
                "polygonFeatureType": "General",
                "polygonInternalZones": {
                    "type": "CIMMaplexInternalZonePriorities",
                    "center": 1
                },
                "polygonPlacementMethod": "HorizontalInPolygon",
                "primaryOffset": 1,
                "primaryOffsetUnit": "Point",
                "removeExtraWhiteSpace": True,
                "repetitionIntervalUnit": "Map",
                "rotationProperties": {
                    "type": "CIMMaplexRotationProperties",
                    "rotationType": "Arithmetic",
                    "alignmentType": "Straight"
                },
                "secondaryOffset": 100,
                "strategyPriorities": {
                    "type": "CIMMaplexStrategyPriorities",
                    "stacking": 1,
                    "overrun": 2,
                    "fontCompression": 3,
                    "fontReduction": 4,
                    "abbreviation": 5
                },
                "thinningDistanceUnit": "Point",
                "truncationMarkerCharacter": ".",
                "truncationMinimumLength": 1,
                "truncationPreferredCharacters": "aeiou"
            },
            "maximumScale": "NaN",
            "minimumScale": "NaN",
            "name": "Class 1",
            "priority": -1,
            "standardLabelPlacementProperties": {
                "type": "CIMStandardLabelPlacementProperties",
                "featureType": "Line",
                "featureWeight": "Low",
                "labelWeight": "High",
                "numLabelsOption": "OneLabelPerName",
                "lineLabelPosition": {
                    "type": "CIMStandardLineLabelPosition",
                    "above": True,
                    "inLine": True,
                    "parallel": True
                },
                "lineLabelPriorities": {
                    "type": "CIMStandardLineLabelPriorities",
                    "aboveStart": 3,
                    "aboveAlong": 3,
                    "aboveEnd": 3,
                    "centerStart": 3,
                    "centerAlong": 3,
                    "centerEnd": 3,
                    "belowStart": 3,
                    "belowAlong": 3,
                    "belowEnd": 3
                },
                "pointPlacementMethod": "AroundPoint",
                "pointPlacementPriorities": {
                    "type": "CIMStandardPointPlacementPriorities",
                    "aboveLeft": 2,
                    "aboveCenter": 2,
                    "aboveRight": 1,
                    "centerLeft": 3,
                    "centerRight": 2,
                    "belowLeft": 3,
                    "belowCenter": 3,
                    "belowRight": 2
                },
                "rotationType": "Arithmetic",
                "polygonPlacementMethod": "AlwaysHorizontal"
            },
            "textSymbol": {
                "type": "CIMSymbolReference",
                "symbol": {
                    "type": "CIMTextSymbol",
                    "blockProgression": "TTB",
                    "depth3D": 1,
                    "extrapolateBaselines": True,
                    "fontEffects": "Normal",
                    "fontEncoding": "Unicode",
                    "fontFamilyName": "Tahoma",
                    "fontStyleName": "Regular",
                    "fontType": "Unspecified",
                    "haloSize": 1,
                    "height": 10,
                    "hinting": "Default",
                    "horizontalAlignment": "Left",
                    "kerning": True,
                    "letterWidth": 100,
                    "ligatures": True,
                    "lineGapType": "ExtraLeading",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        0,
                                        0,
                                        0,
                                        100
                                    ]
                                }
                            }
                        ]
                    },
                    "textCase": "Normal",
                    "textDirection": "LTR",
                    "verticalAlignment": "Bottom",
                    "verticalGlyphOrientation": "Right",
                    "wordSpacing": 100,
                    "billboardMode3D": "FaceNearPlane"
                }
            },
            "useCodedValue": True,
            "visibility": True,
            "iD": -1
        }
        definition.labelVisibility = True
        lyr.setDefinition(definition)
        return

    def make_class_breaks_symb(self, lyr_name):
        """
        Setup lauer 'ClassBreaksRenderer' symbology

        :param lyr_name: The layer name
        """
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "0 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                130,
                                                130,
                                                130,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1 - 10 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                52.5,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 10
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "11 - 100 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                45,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 100
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "101 - 1000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                37.5,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1001 - 5000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                30,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 5000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "5000 - 50000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                22.5,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 50000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "50000 - 100000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                15,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 100000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "100000 - 1000000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                7.5,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1000000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "Upper than 1 million cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                0,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 4620444
                    }
                ],
                "classBreakType": "GraduatedColor",
                "classificationMethod": "Manual",
                "colorRamp": {
                    "type": "CIMPolarContinuousColorRamp",
                    "colorSpace": {
                        "type": "CIMICCColorSpace",
                        "url": "Default RGB"
                    },
                    "fromColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            60,
                            100,
                            96,
                            100
                        ]
                    },
                    "toColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            0,
                            100,
                            96,
                            100
                        ]
                    },
                    "interpolationSpace": "HSV",
                    "polarDirection": "Auto"
                },
                "field": "Confirmed",
                "numberFormat": {
                    "type": "CIMNumericFormat",
                    "alignmentOption": "esriAlignLeft",
                    "alignmentWidth": 0,
                    "roundingOption": "esriRoundNumberOfDecimals",
                    "roundingValue": 6,
                    "zeroPad": True
                },
                "showInAscendingOrder": True,
                "heading": "Confirmed",
                "sampleSize": 10000,
                "defaultSymbolPatch": "Default",
                "defaultSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        130,
                                        130,
                                        130,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "defaultLabel": "0",
                "polygonSymbolColorTarget": "Fill",
                "normalizationType": "Nothing",
                "exclusionLabel": "<excluded>",
                "exclusionSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        255,
                                        0,
                                        0,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "useExclusionSymbol": False,
                "exclusionSymbolPatch": "Default"
            }
            definition.symbolLayerDrawing = {
                "type": "CIMSymbolLayerDrawing"
            }
            definition.visibility = True

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def make_point_class_breaks_symb(self, lyr_name):
        """
        Setup point lauer 'ClassBreaksRenderer' symbology

        :param lyr_name: The layer name
        """
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "\u2264 10 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 1",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    60,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 10
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "11 - 100 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 2",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    52.5,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 100
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "101 - 1000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 3",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    45,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 1000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1001 - 5000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 4",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    37.5,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 5000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "5001 - 50000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 5",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    30,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 50000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "50001 - 100000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 6",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    22.5,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 100000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "100001 - 150000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 7",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    15,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 150000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "150001 - 1000000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 8",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    7.5,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 1000000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "Upper than 1 million cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 9",
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        1.1044549435724839e-15,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMHSVColor",
                                                                "values": [
                                                                    0,
                                                                    100,
                                                                    96,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 4620444
                    }
                ],
                "classBreakType": "GraduatedColor",
                "classificationMethod": "Manual",
                "colorRamp": {
                    "type": "CIMPolarContinuousColorRamp",
                    "colorSpace": {
                        "type": "CIMICCColorSpace",
                        "url": "Default RGB"
                    },
                    "fromColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            60,
                            100,
                            96,
                            100
                        ]
                    },
                    "toColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            0,
                            100,
                            96,
                            100
                        ]
                    },
                    "interpolationSpace": "HSV",
                    "polarDirection": "Auto"
                },
                "field": "Confirmed",
                "numberFormat": {
                    "type": "CIMNumericFormat",
                    "alignmentOption": "esriAlignLeft",
                    "alignmentWidth": 0,
                    "roundingOption": "esriRoundNumberOfDecimals",
                    "roundingValue": 6,
                    "zeroPad": True
                },
                "showInAscendingOrder": True,
                "heading": "Confirmed",
                "sampleSize": 10000,
                "defaultSymbolPatch": "Default",
                "defaultSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPointSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMVectorMarker",
                                "enable": True,
                                "name": "Group 12",
                                "anchorPointUnits": "Relative",
                                "dominantSizeAxis3D": "Z",
                                "size": 4,
                                "billboardMode3D": "FaceNearPlane",
                                "frame": {
                                    "xmin": -2,
                                    "ymin": -2,
                                    "xmax": 2,
                                    "ymax": 2
                                },
                                "markerGraphics": [
                                    {
                                        "type": "CIMMarkerGraphic",
                                        "geometry": {
                                            "curveRings": [
                                                [
                                                    [
                                                        1.2246467991473532e-16,
                                                        2
                                                    ],
                                                    {
                                                        "a": [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            [
                                                                1.1044549435724839e-15,
                                                                0
                                                            ],
                                                            0,
                                                            1
                                                        ]
                                                    }
                                                ]
                                            ]
                                        },
                                        "symbol": {
                                            "type": "CIMPolygonSymbol",
                                            "symbolLayers": [
                                                {
                                                    "type": "CIMSolidStroke",
                                                    "enable": True,
                                                    "capStyle": "Round",
                                                    "joinStyle": "Round",
                                                    "lineStyle3D": "Strip",
                                                    "miterLimit": 10,
                                                    "width": 0.69999999999999996,
                                                    "color": {
                                                        "type": "CIMRGBColor",
                                                        "values": [
                                                            0,
                                                            0,
                                                            0,
                                                            100
                                                        ]
                                                    }
                                                },
                                                {
                                                    "type": "CIMSolidFill",
                                                    "enable": True,
                                                    "color": {
                                                        "type": "CIMRGBColor",
                                                        "values": [
                                                            130,
                                                            130,
                                                            130,
                                                            100
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ],
                                "respectFrame": True
                            }
                        ],
                        "haloSize": 1,
                        "scaleX": 1,
                        "angleAlignment": "Display"
                    }
                },
                "defaultLabel": "<out of range>",
                "polygonSymbolColorTarget": "Fill",
                "normalizationType": "Nothing",
                "exclusionLabel": "<excluded>",
                "exclusionSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPointSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMVectorMarker",
                                "enable": True,
                                "name": "Group 10",
                                "anchorPointUnits": "Relative",
                                "dominantSizeAxis3D": "Z",
                                "size": 4,
                                "billboardMode3D": "FaceNearPlane",
                                "frame": {
                                    "xmin": -2,
                                    "ymin": -2,
                                    "xmax": 2,
                                    "ymax": 2
                                },
                                "markerGraphics": [
                                    {
                                        "type": "CIMMarkerGraphic",
                                        "geometry": {
                                            "curveRings": [
                                                [
                                                    [
                                                        1.2246467991473532e-16,
                                                        2
                                                    ],
                                                    {
                                                        "a": [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            [
                                                                1.1044549435724839e-15,
                                                                0
                                                            ],
                                                            0,
                                                            1
                                                        ]
                                                    }
                                                ]
                                            ]
                                        },
                                        "symbol": {
                                            "type": "CIMPolygonSymbol",
                                            "symbolLayers": [
                                                {
                                                    "type": "CIMSolidStroke",
                                                    "enable": True,
                                                    "capStyle": "Round",
                                                    "joinStyle": "Round",
                                                    "lineStyle3D": "Strip",
                                                    "miterLimit": 10,
                                                    "width": 0.69999999999999996,
                                                    "color": {
                                                        "type": "CIMRGBColor",
                                                        "values": [
                                                            0,
                                                            0,
                                                            0,
                                                            100
                                                        ]
                                                    }
                                                },
                                                {
                                                    "type": "CIMSolidFill",
                                                    "enable": True,
                                                    "color": {
                                                        "type": "CIMRGBColor",
                                                        "values": [
                                                            255,
                                                            0,
                                                            0,
                                                            100
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ],
                                "respectFrame": True
                            }
                        ],
                        "haloSize": 1,
                        "scaleX": 1,
                        "angleAlignment": "Display"
                    }
                },
                "useExclusionSymbol": False,
                "exclusionSymbolPatch": "Default",
                "visualVariables": [
                    {
                        "type": "CIMSizeVisualVariable",
                        "authoringInfo": {
                            "type": "CIMVisualVariableAuthoringInfo",
                            "maxSliderValue": 66741,
                            "showLegend": True,
                            "heading": "Deaths"
                        },
                        "randomMax": 1,
                        "minSize": 5,
                        "maxSize": 50,
                        "maxValue": 66741,
                        "valueRepresentation": "Radius",
                        "variableType": "Graduated",
                        "valueShape": "Unknown",
                        "axis": "HeightAxis",
                        "normalizationType": "Nothing",
                        "valueExpressionInfo": {
                            "type": "CIMExpressionInfo",
                            "title": "Custom",
                            "expression": "$feature.Deaths",
                            "returnType": "Default"
                        }
                    }
                ]
            }
            definition.symbolLayerDrawing = {
                "type": "CIMSymbolLayerDrawing",
                "symbolLayers": [
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 1"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 2"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 3"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 4"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 5"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 6"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 7"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 8"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 9"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 10"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 11"
                    },
                    {
                        "type": "CIMSymbolLayerIdentifier",
                        "symbolLayerName": "Group 12"
                    }
                ]
            }
            definition.visibility = True

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def make_simple_symb(self, lyr_name):
        """
        Setup simple class symbology

        :param lyr_name: The layer name
        """
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "\u2264 4000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                255,
                                                255,
                                                204,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 4000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "4001 - 16000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                217,
                                                240,
                                                163,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 16000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "16001 - 33000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                173,
                                                221,
                                                142,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 33000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "33000 - 53000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                120,
                                                198,
                                                121,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 53000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "53001 - 80000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                49,
                                                163,
                                                84,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 80000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "Upper than 80000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                104,
                                                55,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1107013
                    }
                ],
                "classBreakType": "GraduatedColor",
                "classificationMethod": "Manual",
                "colorRamp": {
                    "type": "CIMFixedColorRamp",
                    "colorSpace": {
                        "type": "CIMICCColorSpace",
                        "url": "Default RGB"
                    },
                    "colors": [
                        {
                            "type": "CIMRGBColor",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "values": [
                                255,
                                255,
                                204,
                                100
                            ]
                        },
                        {
                            "type": "CIMRGBColor",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "values": [
                                217,
                                240,
                                163,
                                100
                            ]
                        },
                        {
                            "type": "CIMRGBColor",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "values": [
                                173,
                                221,
                                142,
                                100
                            ]
                        },
                        {
                            "type": "CIMRGBColor",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "values": [
                                120,
                                198,
                                121,
                                100
                            ]
                        },
                        {
                            "type": "CIMRGBColor",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "values": [
                                49,
                                163,
                                84,
                                100
                            ]
                        },
                        {
                            "type": "CIMRGBColor",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "values": [
                                0,
                                104,
                                55,
                                100
                            ]
                        }
                    ]
                },
                "field": "Recovred",
                "numberFormat": {
                    "type": "CIMNumericFormat",
                    "alignmentOption": "esriAlignLeft",
                    "alignmentWidth": 0,
                    "roundingOption": "esriRoundNumberOfDecimals",
                    "roundingValue": 6,
                    "zeroPad": True
                },
                "showInAscendingOrder": True,
                "heading": "Recovred",
                "sampleSize": 10000,
                "defaultSymbolPatch": "Default",
                "defaultSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        130,
                                        130,
                                        130,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "defaultLabel": "<out of range>",
                "polygonSymbolColorTarget": "Fill",
                "normalizationType": "Nothing",
                "exclusionLabel": "<excluded>",
                "exclusionSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        255,
                                        0,
                                        0,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "useExclusionSymbol": False,
                "exclusionSymbolPatch": "Default"
            }
            definition.symbolLayerDrawing = {
                "type": "CIMSymbolLayerDrawing"
            }
            definition.visibility = True

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def make_time_related_symb(self, lyr_name, time_field):
        """
        Setup time related symbology

        :param lyr_name: The layer name
        :param time_field: Time field
        """
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            """Setting time."""
            definition.featureTable.timeFields = {
                "type": "CIMTimeTableDefinition",
                "startTimeField": time_field,
                "timeValueFormat": "yyyy-MM-dd HH:mm:ss"
            }
            definition.featureTable.timeDefinition = {
                "type": "CIMTimeDataDefinition",
                "useTime": True,
                "customTimeExtent": {
                    "type": "TimeExtent",
                    "start": 1579651200000,
                    "end": 1594080000000,
                    "empty": False
                }
            }

            """Confirmed."""
            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "\u226410 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                51.43,
                                                74.120000000000005,
                                                100,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 10
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "11 - 100 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                102.03,
                                                77.25,
                                                100,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 100
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "101 - 1000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                152.78,
                                                80.390000000000001,
                                                100,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1001 - 5000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                203.21000000000001,
                                                83.140000000000001,
                                                100,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 5000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "5001 - 50000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                253.63999999999999,
                                                86.269999999999996,
                                                100,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 50000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "50001 - 100000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                351.82999999999998,
                                                66.659999999999997,
                                                65.099999999999994,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 100000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "100001 - 150000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                304.20999999999998,
                                                89.409999999999997,
                                                100,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 150000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "150001 - 1000000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMHSVColor",
                                            "values": [
                                                0,
                                                100,
                                                100,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1000000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "Upper than 1 million cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.69999999999999996,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                110,
                                                110,
                                                110,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                115,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 4620444
                    }
                ],
                "classBreakType": "GraduatedColor",
                "classificationMethod": "Manual",
                "colorRamp": {
                    "type": "CIMPolarContinuousColorRamp",
                    "colorSpace": {
                        "type": "CIMICCColorSpace",
                        "url": "Default RGB"
                    },
                    "fromColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            60,
                            100,
                            96,
                            100
                        ]
                    },
                    "toColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            0,
                            100,
                            96,
                            100
                        ]
                    },
                    "interpolationSpace": "HSV",
                    "polarDirection": "Auto"
                },
                "field": "Confirmed",
                "minimumBreak": 1,
                "numberFormat": {
                    "type": "CIMNumericFormat",
                    "alignmentOption": "esriAlignLeft",
                    "alignmentWidth": 0,
                    "roundingOption": "esriRoundNumberOfDecimals",
                    "roundingValue": 6,
                    "zeroPad": True
                },
                "showInAscendingOrder": True,
                "heading": "Confirmed",
                "sampleSize": 10000,
                "defaultSymbolPatch": "Default",
                "defaultSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        130,
                                        130,
                                        130,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "defaultLabel": "0 cases",
                "polygonSymbolColorTarget": "Fill",
                "normalizationType": "Nothing",
                "exclusionLabel": "<excluded>",
                "exclusionSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        255,
                                        0,
                                        0,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "useExclusionSymbol": False,
                "exclusionSymbolPatch": "Default"
            }

            definition.visibility = True

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            """Recovred rate."""
            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "backgroundSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        166,
                                        166,
                                        166,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        166,
                                        166,
                                        166,
                                        0
                                    ]
                                }
                            }
                        ]
                    }
                },
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "\u2264 2%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 4,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        6.6030623875207053e-16,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    76,
                                                                    115,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 0.015779620219309978
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "2 - 8%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 6.3333333333333339,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        6.6030623875207053e-16,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    76,
                                                                    115,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 0.083333333333333329
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "8 - 22%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 8.6666666666666679,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        6.6030623875207053e-16,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    76,
                                                                    115,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 0.21818181818181817
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "22 - 33%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 11.000000000000002,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        6.6030623875207053e-16,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    76,
                                                                    115,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 0.33431085043988268
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "33 - 69%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 13.333333333333336,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        6.6030623875207053e-16,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    76,
                                                                    115,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 0.68624064478986757
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "69 - 100%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Z",
                                        "size": 18,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": -2,
                                            "ymin": -2,
                                            "xmax": 2,
                                            "ymax": 2
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                1.2246467991473532e-16,
                                                                2
                                                            ],
                                                            {
                                                                "a": [
                                                                    [
                                                                        1.2246467991473532e-16,
                                                                        2
                                                                    ],
                                                                    [
                                                                        6.6030623875207053e-16,
                                                                        0
                                                                    ],
                                                                    0,
                                                                    1
                                                                ]
                                                            }
                                                        ]
                                                    ]
                                                },
                                                "symbol": {
                                                    "type": "CIMPolygonSymbol",
                                                    "symbolLayers": [
                                                        {
                                                            "type": "CIMSolidStroke",
                                                            "enable": True,
                                                            "capStyle": "Round",
                                                            "joinStyle": "Round",
                                                            "lineStyle3D": "Strip",
                                                            "miterLimit": 10,
                                                            "width": 0.69999999999999996,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "type": "CIMSolidFill",
                                                            "enable": True,
                                                            "color": {
                                                                "type": "CIMRGBColor",
                                                                "values": [
                                                                    76,
                                                                    115,
                                                                    0,
                                                                    100
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        },
                        "upperBound": 1
                    }
                ],
                "classBreakType": "GraduatedSymbol",
                "classificationMethod": "NaturalBreaks",
                "colorRamp": {
                    "type": "CIMPolarContinuousColorRamp",
                    "colorSpace": {
                        "type": "CIMICCColorSpace",
                        "url": "Default RGB"
                    },
                    "fromColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            60,
                            100,
                            96,
                            100
                        ]
                    },
                    "toColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            0,
                            100,
                            96,
                            100
                        ]
                    },
                    "interpolationSpace": "HSV",
                    "polarDirection": "Auto"
                },
                "numberFormat": {
                    "type": "CIMPercentageFormat",
                    "alignmentOption": "esriAlignLeft",
                    "alignmentWidth": 12,
                    "roundingOption": "esriRoundNumberOfDecimals",
                    "roundingValue": 0,
                    "adjustPercentage": True
                },
                "showInAscendingOrder": True,
                "heading": "Recovred rate.",
                "sampleSize": 10000,
                "defaultSymbolPatch": "Default",
                "defaultSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        130,
                                        130,
                                        130,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "defaultLabel": "<out of range>",
                "valueExpressionInfo": {
                    "type": "CIMExpressionInfo",
                    "title": "Recovred rate.",
                    "expression": "$feature.Recovred/$feature.Confirmed",
                    "returnType": "Default"
                },
                "polygonSymbolColorTarget": "Fill",
                "normalizationType": "Nothing",
                "exclusionLabel": "<excluded>",
                "exclusionSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        255,
                                        0,
                                        0,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "useExclusionSymbol": False,
                "exclusionSymbolPatch": "Default"
            }
            definition.symbolLayerDrawing = {
                "type": "CIMSymbolLayerDrawing"
            }
            definition.visibility = True

            lyr.setDefinition(definition)

            self.active_map.addLayer(lyr, 'TOP')

            """Deaths rate."""
            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "\u2264 5%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.40000000000000002,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMPictureFill",
                                        "enable": True,
                                        "url": "data:image/bmp;base64,Qk3+AwAAAAAAAD4AAAAoAAAATAAAAFAAAAABAAEAAAAAAMADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP///wD//+//f///f//wAABu7v/7/9v//3+wAAD///3f9v+39/fwAAD/////v///f//wAADu7+/9/+3//39wAAB//3/f/7939+/wAAD/9/7/3f//f//wAAD////+//f//33QAAD3f/fv9//v9//wAAD/979//779//fwAAC//v//v////v+wAAD7v/v3/vf/v//wAAD/+/+/9/+3/73wAAD//6/9/93/9//QAAB27/3v///9///wAAD//v//9vf//+7wAAD//99/f/7ffv/wAADtu//7///////wAAB//3ff3bf77/bQAAD///////7//7/wAAD7bd7+///fff/wAADf///363f3//3wAAD///vfv/79/+/QAAD+23/+///ff//wAAB3//d7/t//7v/wAAD////v9/33//twAADdtu3/v/++/9/gAAD////f/////f/wAAD3//v9/tvv7/twAAC//9//9///v9/gAAD/tv93v/d9/3/wAAD9//v/////7//wAAD3/9/++7///f2wAAC///9v3/dvf+/wAAD/tuv9///79//gAAD///9/+79//3/wAAD7/9/3v/f93/fwAADf2////793/f9wAAD//33e9//////wAAD/f////f+/u73QAADb9+9vv9v7///wAAD////7///u///wAAD/vv3++/+/7vdwAAC//////237v//gAAD299uvv//f+//wAAD////7///9/27wAADf/v7+9/7/f/+wAAD+//f3fbf37d3wAAD/99+/3/+9///wAAB///7/99//v/9wAADvvvf3f/3f/3fgAAD/99+/7v/7///wAAD9//7///fvW93wAAB/fvf2377///+wAAD/99/f+//3/3fwAAD3//7//u99W//wAAB/3v/2t////97wAADe//ff/7vf///QAAD/979+/f/7W3vwAAD7vf/37/7////wAAB////f/7/f//9wAADe7+v7fff7bffwAAD3/39/77/////wAAD/t/////7tv7/wAAD7///f//f///3wAAB/3ff37b/7/f+wAAD/f97///93f/fwAADt9////7v/+3/wAAD//v/dve/d3/7wAAB/v+7////////wAADd9//v7bbve3fQAAD///9/f//////wAAD/vvf//+2/797wAAC7993v9v/2/v/wAAD/////f////+/wAADvf/d9/22/3//QAAB/7b/3+//3/f7wAAD9//3fv///f/fwAAD32//7/rd/73/wAAC//3t/7//3/+7wAAA=",
                                        "scaleX": 1,
                                        "height": 60,
                                        "textureFilter": "Draft",
                                        "colorSubstitutions": [
                                            {
                                                "type": "CIMColorSubstitution",
                                                "oldColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        0,
                                                        0,
                                                        0,
                                                        100
                                                    ]
                                                },
                                                "newColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        0,
                                                        0,
                                                        0,
                                                        100
                                                    ]
                                                }
                                            },
                                            {
                                                "type": "CIMColorSubstitution",
                                                "oldColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        255,
                                                        255,
                                                        255,
                                                        100
                                                    ]
                                                },
                                                "newColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        255,
                                                        255,
                                                        255,
                                                        0
                                                    ]
                                                }
                                            }
                                        ],
                                        "tintColor": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                255,
                                                255,
                                                255,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 0.050000000000000003
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "5 - 20%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.40000000000000002,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMPictureFill",
                                        "enable": True,
                                        "url": "data:image/bmp;base64,Qk0+AgAAAAAAAD4AAAAoAAAAQAAAAEAAAAABAAEAAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP///wD3/j5/9/4+f///z4///8+P/z//3/8//9//x/+//8f/v7/v/3+/7/9/f97//3/e////vn/+/75//n/+vfx//r38nv3d35793d/8/f6//P3+v/r//n/6//5/t39+/7d/fv+/f7/7v3+/+3//3/1//9/9f9+Pfn/fj35/vn7/f75+//9//f//f/3//j/4//4/+P//z/8//8//P7/+//+//v//n/z/+Z/8//mv+v/Hr/r/x3f3fu93937vf/9u93//bvf///X7///1+/5/+f/+f/n//4/9//+P/f//3//3/9//9/u///P7v//zu3/f9bt/3/XX/7/u1/+/7uf/f+/n/3/v9/4+f/f+Pn///8+P///Pj/8//9//P//f/8f/v//H/7+/7/9/v+//f3/e//9/3v///75//v++f/5//r38f/69/J793d+e/d3f/P3+v/z9/r/6//5/+v/+f7d/fv+3f37/v3+/+79/v/t//9/9f//f/X/fj35/349+f75+/3++fv//f/3//3/9//4/+P/+P/j//8//P//P/z+//v//v/7//5/8//mf/P/5r/r/x6/6/8d3937vd/d+73//bvd//273///1+///9fv+f/n//n/5//+P/f//j/3//9//9//f//f7v//z+7//87t/3/W7f9/11/+/7tf/v+7n/3/v5/9/7w==",
                                        "scaleX": 1,
                                        "height": 48,
                                        "textureFilter": "Draft",
                                        "colorSubstitutions": [
                                            {
                                                "type": "CIMColorSubstitution",
                                                "oldColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        0,
                                                        0,
                                                        0,
                                                        100
                                                    ]
                                                },
                                                "newColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        0,
                                                        0,
                                                        0,
                                                        100
                                                    ]
                                                }
                                            },
                                            {
                                                "type": "CIMColorSubstitution",
                                                "oldColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        255,
                                                        255,
                                                        255,
                                                        100
                                                    ]
                                                },
                                                "newColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        255,
                                                        255,
                                                        255,
                                                        0
                                                    ]
                                                }
                                            }
                                        ],
                                        "tintColor": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                255,
                                                255,
                                                255,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 0.20000000000000001
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "20 - 50%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.40000000000000002,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMHatchFill",
                                        "enable": True,
                                        "lineSymbol": {
                                            "type": "CIMLineSymbol",
                                            "symbolLayers": [
                                                {
                                                    "type": "CIMSolidStroke",
                                                    "enable": True,
                                                    "capStyle": "Butt",
                                                    "joinStyle": "Miter",
                                                    "lineStyle3D": "Strip",
                                                    "miterLimit": 10,
                                                    "width": 0.5,
                                                    "color": {
                                                        "type": "CIMRGBColor",
                                                        "values": [
                                                            0,
                                                            0,
                                                            0,
                                                            100
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        "rotation": 135,
                                        "separation": 5
                                    }
                                ]
                            }
                        },
                        "upperBound": 0.5
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "50 - 100%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 0.40000000000000002,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMPictureFill",
                                        "enable": True,
                                        "url": "data:image/bmp;base64,Qk3+AwAAAAAAAD4AAAAoAAAARgAAAFAAAAABAAEAAAAAAMADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP///wD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+3+/+gAAAC/+/2/+/2/+/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+39/9gAAAC/+/2/+/1/9/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+3+/+gAAAC/+/2/+/2/+/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+39/9gAAAC/+/2/+/1/9/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+3+/+gAAAC/+/2/+/2/+/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+39/9gAAAC/+/2/+/1/9/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+3+/+gAAAC/+/2/+/2/+/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAD/7///7///v/wAAAD/r+//r+/+v7wAAADv6//v6/+/r/wAAAD/7///7///v/wAAAAAAAAAAAAAAAAAAAD///3///3///gAAAD+/+3+/+39/9gAAAC/+/2/+/1/9/gAAAD///3///3///gAAAAAAAAAAAAAAAAAAAA=",
                                        "scaleX": 1,
                                        "height": 60,
                                        "textureFilter": "Draft",
                                        "colorSubstitutions": [
                                            {
                                                "type": "CIMColorSubstitution",
                                                "oldColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        0,
                                                        0,
                                                        0,
                                                        100
                                                    ]
                                                },
                                                "newColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        0,
                                                        0,
                                                        0,
                                                        100
                                                    ]
                                                }
                                            },
                                            {
                                                "type": "CIMColorSubstitution",
                                                "oldColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        255,
                                                        255,
                                                        255,
                                                        100
                                                    ]
                                                },
                                                "newColor": {
                                                    "type": "CIMRGBColor",
                                                    "values": [
                                                        255,
                                                        255,
                                                        255,
                                                        0
                                                    ]
                                                }
                                            }
                                        ],
                                        "tintColor": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                255,
                                                255,
                                                255,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1
                    }
                ],
                "classBreakType": "GraduatedColor",
                "classificationMethod": "Manual",
                "colorRamp": {
                    "type": "CIMPolarContinuousColorRamp",
                    "colorSpace": {
                        "type": "CIMICCColorSpace",
                        "url": "Default RGB"
                    },
                    "fromColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            60,
                            100,
                            96,
                            100
                        ]
                    },
                    "toColor": {
                        "type": "CIMHSVColor",
                        "values": [
                            0,
                            100,
                            96,
                            100
                        ]
                    },
                    "interpolationSpace": "HSV",
                    "polarDirection": "Auto"
                },
                "numberFormat": {
                    "type": "CIMPercentageFormat",
                    "alignmentOption": "esriAlignLeft",
                    "alignmentWidth": 12,
                    "roundingOption": "esriRoundNumberOfDecimals",
                    "roundingValue": 2,
                    "adjustPercentage": True
                },
                "showInAscendingOrder": True,
                "heading": "Deaths rate.",
                "sampleSize": 10000,
                "defaultSymbolPatch": "Default",
                "defaultSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        130,
                                        130,
                                        130,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "defaultLabel": "<out of range>",
                "valueExpressionInfo": {
                    "type": "CIMExpressionInfo",
                    "title": "Deaths rate.",
                    "expression": "$feature.Deaths/$feature.Confirmed",
                    "returnType": "Default"
                },
                "polygonSymbolColorTarget": "Fill",
                "normalizationType": "Nothing",
                "exclusionLabel": "<excluded>",
                "exclusionSymbol": {
                    "type": "CIMSymbolReference",
                    "symbol": {
                        "type": "CIMPolygonSymbol",
                        "symbolLayers": [
                            {
                                "type": "CIMSolidStroke",
                                "enable": True,
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        110,
                                        110,
                                        110,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        255,
                                        0,
                                        0,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                },
                "useExclusionSymbol": False,
                "exclusionSymbolPatch": "Default"
            }
            definition.symbolLayerDrawing = {
                "type": "CIMSymbolLayerDrawing"
            }
            definition.visibility = True

            lyr.setDefinition(definition)

            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def setTimeCursor(self, lyr_name, time_field):
        """
        Activate the time cursor

        :param lyr_name: The timed layer name
        :param time_field: Time field
        """
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.featureTable.timeFields = {
                "type": "CIMTimeTableDefinition",
                "startTimeField": time_field,
                "timeValueFormat": "yyyy-MM-dd HH:mm:ss"
            }

            definition.featureTable.timeDefinition = {
                "type": "CIMTimeDataDefinition",
                "useTime": True,
                "customTimeExtent": {
                    "type": "TimeExtent",
                    "start": 1579651200000,
                    "end": 1594080000000,
                    "empty": False
                }
            }

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def reset_lyrs(self):
        """
        Reset all layers
        """
        try:
            [self.active_map.removeLayer(lyr) for lyr in self.active_map.listLayers()]

            [self.active_map.addLayer(arcpy.MakeFeatureLayer_management(t, t).getOutput(0), 'TOP')
             for t in arcpy.ListFeatureClasses()]

            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def hide(self, lyr_name):
        """
        Hide layer

        :param lyr_name: The layer name
        """
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.visibility = False

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'BOTTOM')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return


app = wx.App()
Pivot(None, title='Pivot')
app.MainLoop()
