"""
-------------------------------------------------------------------------
    Tool:               Pivot
    Source Name:        Pivot.py
    Author:             M'hamed Bendenia.
-------------------------------------------------------------------------
"""

from numba import jit, cuda
from random import randrange
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# import geopandas as gpd
import arcpy
from arcgis import GIS
import os
import sys
import time
import wx
import pathlib


class Pivot(wx.Frame):
    workspace = None  # default gdb path
    workfolder = None  # default gdb folder path
    aprx = arcpy.mp.ArcGISProject("CURRENT")  # current project
    active_map = None  # current map

    data_warehouse = {}
    Fact = None
    sizer = wx.GridBagSizer(0, 0)
    panel = None
    axes = None
    bmp = None
    xChoice = yChoice = zChoice = None
    Fc = None
    inc = 0

    x = y = z = None

    """Define default GDB if parameter is Null"""
    if len(arcpy.GetParameterAsText(0)) == 0:
        workspace = arcpy.env.workspace
        workfolder = os.path.dirname(workspace)
    else:
        workspace = arcpy.GetParameter(0)
        arcpy.env.workspace = workspace
        workfolder = os.path.dirname(arcpy.env.workspace)

    """Define current map if parameter is Null"""
    if len(arcpy.GetParameterAsText(1)) == 0:
        active_map = aprx.listMaps()[0]
    else:
        active_map = aprx.listMaps(arcpy.GetParameter(1))[0]

    """Putting all layers in a dict"""
    lyr_dict = {lyr.name.lower(): lyr for lyr in active_map.listLayers()}

    def __init__(self, parent, title):
        super(Pivot, self).__init__(parent, title=title, size=wx.Size(410, 250),
                                    style=wx.STAY_ON_TOP ^ wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):

        self.panel = wx.Panel(self)
        self.local = wx.Locale(wx.LANGUAGE_DEFAULT)

        """Axes image"""
        self.bmp = wx.Bitmap(str(pathlib.Path().absolute().joinpath(r"Scripts\Axes.png")), wx.BITMAP_TYPE_PNG)
        self.axes = wx.StaticBitmap(self.panel, wx.ID_ANY, self.bmp, wx.DefaultPosition, (120, 120), 0)
        self.axes.Bind(wx.EVT_LEFT_DOWN, self.onAxesClick)
        self.sizer.Add(self.axes, pos=(1, 1), flag=wx.ALL, border=5)

        """The lists of choices"""
        self.xChoice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, size=wx.Size(120, 25), style=0)
        self.xChoice.Bind(wx.EVT_CHOICE, self.onXChoiceClick)
        self.sizer.Add(self.xChoice, pos=(2, 2), flag=wx.ALL, border=5)

        self.yChoice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, size=wx.Size(120, 25), style=0)
        self.yChoice.Bind(wx.EVT_CHOICE, self.onYChoiceClick)
        self.sizer.Add(self.yChoice, pos=(0, 1), flag=wx.ALL, border=5)

        self.zChoice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, size=wx.Size(120, 25), style=0)
        self.zChoice.Bind(wx.EVT_CHOICE, self.onZChoiceClick)
        self.sizer.Add(self.zChoice, pos=(2, 0), flag=wx.ALL, border=5)

        """Filling the DW and the lists by feature classes"""
        for fc in arcpy.ListFeatureClasses():
            try:
                self.data_warehouse[fc.title().lower()] = pd.DataFrame.spatial.from_featureclass(fc)
                self.xChoice.Append(fc.title())
                self.yChoice.Append(fc.title())
                self.zChoice.Append(fc.title())
            except Exception as e:
                arcpy.AddError(str(e))

        """Filling the DW and the lists by tables"""
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
        if self.yChoice.GetSelection() == wx.NOT_FOUND or self.zChoice.GetSelection() == wx.NOT_FOUND:
            return
        else:
            self.pivotRun()

    def onYChoiceClick(self, event):
        if self.zChoice.GetSelection() == wx.NOT_FOUND or self.zChoice.GetSelection() == wx.NOT_FOUND:
            return
        else:
            self.pivotRun()

    def onZChoiceClick(self, event):
        if self.yChoice.GetSelection() == wx.NOT_FOUND or self.xChoice.GetSelection() == wx.NOT_FOUND:
            return
        else:
            self.pivotRun()

    def pivotRun(self):
        """ 'String'  ('SmallInteger'  'Integer')  ('Double' 'Single')  'Date' 'Geometry' """
        arcpy.AddMessage("---------------------")
        if self.xChoice.GetString(self.xChoice.GetSelection()).lower() == "date_world_cases":
            if self.yChoice.GetString(self.yChoice.GetSelection()).lower() == "covid_cases":
                arcpy.AddMessage("3")

                """Z with Z.fields[0] as label"""
                self.makeLabel(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                               field_name="Country_Re")

                """Z symbolized with Z.fields[3]"""
                self.makeSymb(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())

                self.reset_lyr(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())

                """Plot X(time) Y(point)"""
                self.stackPlot(data_name="covid_cases")

            else:
                arcpy.AddMessage("6")

                """Time cursor X"""
                self.setTimeCursor(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower(),
                                   time_field="Date")

                """Y symbolized with Y.fields[3]"""
                self.makeSymb(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())

                self.reset_lyr(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())

                """Plot X(states) Y(count_accidents)"""
                self.graphPlot(data_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())

        elif self.xChoice.GetString(self.xChoice.GetSelection()).lower() == "covid_cases":
            if self.yChoice.GetString(self.yChoice.GetSelection()).lower() == "date_world_cases":
                arcpy.AddMessage("4")

                self.reset_lyr(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())
                self.reset_lyr(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())
                self.makeLabel(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                               field_name="Country_Re")

                self.linePlot(data_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())
            else:
                arcpy.AddMessage("2")

                self.reset_lyr(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())
                self.makeSymb2(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())
                self.setTimeCursor(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                                   time_field="Date")
                self.makePointSymb(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())
                self.setTimeCursor(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower(),
                                   time_field="Date")

        elif self.xChoice.GetString(self.xChoice.GetSelection()).lower() == "world_cases":
            if self.yChoice.GetString(self.yChoice.GetSelection()).lower() == "date_world_cases":
                arcpy.AddMessage("5")

                self.reset_lyr(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())
                self.reset_lyr(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())
                self.makeSymb(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())
                self.rateLinePlot(data_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())
            else:
                arcpy.AddMessage("1")
                self.reset_lyr(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())
                self.reset_lyr(lyr_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower())
                self.makeSymb3(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())
                self.setTimeCursor(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                                   time_field="Date")
        else:
            arcpy.AddWarning("This position is not supported.")
        return

    def rateLinePlot(self, data_name):
        # lineplot
        df_temp = self.data_warehouse[data_name].groupby("Date")["Confirmed", "Deaths", "Recovred"].max().reset_index()

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
        # lineplot
        df_temp = self.data_warehouse[data_name].groupby("Date")["Confirmed", "Deaths", "Recovred"].max().reset_index()

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

    def reset_lyr(self, lyr_name):
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMSimpleRenderer",
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
                                        252.44999999999999,
                                        228.13,
                                        209.53,
                                        100
                                    ]
                                }
                            }
                        ]
                    }
                }
            }

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'BOTTOM')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def graphPlot(self, data_name):
        try:
            df_temp = self.data_warehouse[data_name].groupby("Country_Re")["Confirmed",
                                                                           "Deaths", "Recovred"].max().reset_index()
        except Exception as e:
            arcpy.AddError(str(e))

        ind = np.arange(df_temp.Country_Re.count())  # the x locations for the groups
        f, ax = plt.subplots(figsize=(20, 5))

        p1 = ax.bar(ind - 0.25, df_temp.Confirmed, 0.25, color=(0.95, 0.62, 0.07, 1), picker=6)
        p2 = ax.bar(ind, df_temp.Recovred, 0.25, color=(0.12, 0.52, 0.29, 1), picker=6)
        p3 = ax.bar(ind + 0.25, df_temp.Deaths, 0.25, color=(1, 0, 0, 1), picker=6)

        def on_pick(event):
            rect = event.artist
            height = rect.get_height()
            try:
                ann = ax.annotate('{}'.format(height),
                                  xy=(rect.get_x() + rect.get_width() / 2, height),
                                  xytext=(0, 3),  # 3 points vertical offset
                                  textcoords="offset points",
                                  ha='center', va='bottom')
                plt.pause(1)
                ann.remove()
                fig.canvas.draw()
            except Exception as e:
                print(str(e))

        f.canvas.mpl_connect('pick_event', on_pick)

        ax.set_title('Confirmed, Recovred and Deaths numbers by Country_Region.')
        plt.xticks(ind, df_temp.Country_Re)
        plt.xticks(rotation=90)
        ax.set_yscale('symlog')
        ax.legend((p1[0], p2[0], p3[0]), ('Confirmed', 'Recovred', 'Deaths'))
        plt.margins(x=0.01)
        plt.tick_params(axis="x", width=0.75)
        plt.tight_layout()
        plt.show()
        return

    def stackPlot(self, data_name):
        df_temp = self.data_warehouse[data_name].groupby("Date")[
            "Confirmed", "Deaths", "Recovred"].max().reset_index()

        fig, ax = plt.subplots()
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
        lyr = self.lyr_dict[lyr_name]
        definition = lyr.getDefinition('V2')
        definition.labelClasses[0].expression = '$feature.' + field_name
        definition.labelClasses[0].maplexLabelPlacementProperties.enablePolygonFixedPosition = True
        definition.labelVisibility = True
        lyr.setDefinition(definition)
        return

    def makePointSymb(self, lyr_name):
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
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
                                        "anchorPoint": {
                                            "x": 0,
                                            "y": 0,
                                            "z": 0
                                        },
                                        "anchorPointUnits": "Relative",
                                        "dominantSizeAxis3D": "Y",
                                        "size": 10,
                                        "billboardMode3D": "FaceNearPlane",
                                        "frame": {
                                            "xmin": 0,
                                            "ymin": 0,
                                            "xmax": 17,
                                            "ymax": 17
                                        },
                                        "markerGraphics": [
                                            {
                                                "type": "CIMMarkerGraphic",
                                                "geometry": {
                                                    "curveRings": [
                                                        [
                                                            [
                                                                17,
                                                                8.5
                                                            ],
                                                            {
                                                                "b": [
                                                                    [
                                                                        8.5,
                                                                        0
                                                                    ],
                                                                    [
                                                                        17,
                                                                        3.81000000000000005
                                                                    ],
                                                                    [
                                                                        13.19,
                                                                        0
                                                                    ]
                                                                ]
                                                            },
                                                            {
                                                                "b": [
                                                                    [
                                                                        0,
                                                                        8.5
                                                                    ],
                                                                    [
                                                                        3.81000000000000005,
                                                                        0
                                                                    ],
                                                                    [
                                                                        0,
                                                                        3.81000000000000005
                                                                    ]
                                                                ]
                                                            },
                                                            {
                                                                "b": [
                                                                    [
                                                                        8.5,
                                                                        17
                                                                    ],
                                                                    [
                                                                        0,
                                                                        13.19
                                                                    ],
                                                                    [
                                                                        3.81000000000000005,
                                                                        17
                                                                    ]
                                                                ]
                                                            },
                                                            {
                                                                "b": [
                                                                    [
                                                                        17,
                                                                        8.5
                                                                    ],
                                                                    [
                                                                        13.19,
                                                                        17
                                                                    ],
                                                                    [
                                                                        17,
                                                                        13.19
                                                                    ]
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
                                                            "width": 0,
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
                                                                    0,
                                                                    0,
                                                                    0,
                                                                    0
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ],
                                        "scaleSymbolsProportionally": True,
                                        "respectFrame": True
                                    }
                                ],
                                "haloSize": 1,
                                "scaleX": 1,
                                "angleAlignment": "Display"
                            }
                        }
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1 case",
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
                                                                        5.960787254351244e-15,
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
                                                                    42.859999999999999,
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
                        "upperBound": 1
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "2 - 5 cases",
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
                                                                        5.960787254351244e-15,
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
                                                                    34.280000000000001,
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
                        "upperBound": 5
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "6 - 10 cases",
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
                                                                        5.960787254351244e-15,
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
                                                                    25.719999999999999,
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
                        "label": "11 - 20 cases",
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
                                                                        5.960787254351244e-15,
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
                                                                    17.140000000000001,
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
                        "upperBound": 20
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "21 - 50 cases",
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
                                                                        5.960787254351244e-15,
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
                                                                    8.5700000000000003,
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
                        "upperBound": 50
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "51 - 100 cases",
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
                                                                        5.960787254351244e-15,
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
                        "upperBound": 100
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "101 - 500 cases",
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
                                                                        5.960787254351244e-15,
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
                        "upperBound": 500
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "501 - 1000 cases",
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
                                                                        5.960787254351244e-15,
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
                        "upperBound": 1000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1001 - 2000 cases",
                        "patch": "Default",
                        "symbol": {
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
                                                                        5.960787254351244e-15,
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
                        "upperBound": 2000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "2001 - 3000 cases",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPointSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMVectorMarker",
                                        "enable": True,
                                        "name": "Group 11",
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
                                                                        5.960787254351244e-15,
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
                        "upperBound": 3000
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "3001 - 7000 cases",
                        "patch": "Default",
                        "symbol": {
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
                                                                        5.960787254351244e-15,
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
                        "upperBound": 67666
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
                    "alignmentWidth": 12,
                    "roundingOption": "esriRoundNumberOfDecimals",
                    "roundingValue": 6
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
                                "name": "Group 13",
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
                                                                6.2329709636141858e-15,
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
                                                                6.2329709636141858e-15,
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
                            "maxSliderValue": 2959,
                            "showLegend": True,
                            "heading": "Deaths"
                        },
                        "randomMax": 1,
                        "minSize": 5,
                        "maxSize": 50,
                        "minValue": 1,
                        "maxValue": 2959,
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

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def makeSymb(self, lyr_name):
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "1 case",
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
                                                60,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "2 - 4 cases",
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
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 4
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "5 - 9 cases",
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
                                                42.859999999999999,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 9
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "10 - 16 cases",
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
                                                34.280000000000001,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 16
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "17 - 28 cases",
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
                                                25.719999999999999,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 28
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "29 - 61 cases",
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
                                                17.140000000000001,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 61
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "62 - 761 cases",
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
                                                8.5700000000000003,
                                                100,
                                                96,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 761
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "762 - 66907 cases",
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
                        "upperBound": 66907
                    }
                ],
                "classBreakType": "GraduatedColor",
                "classificationMethod": "Quantile",
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
                "useDefaultSymbol": True,
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

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def makeSymb2(self, lyr_name):
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
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
                                                0
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
                                                0
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1 case",
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
                                                64.459999999999994,
                                                100,
                                                90.340000000000003,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "2 cases",
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
                                                68.930000000000007,
                                                100,
                                                84.689999999999998,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 2
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "3 - 5 cases",
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
                                                73.390000000000001,
                                                100,
                                                79.030000000000001,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 5
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "6 - 11 cases",
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
                                                77.859999999999999,
                                                100,
                                                73.379999999999995,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 11
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "12 - 16 cases",
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
                                                82.319999999999993,
                                                100,
                                                67.719999999999999,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 16
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "17 - 29 cases",
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
                                                86.780000000000001,
                                                100,
                                                62.07,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 29
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "30 - 78 cases",
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
                                                91.25,
                                                100,
                                                56.409999999999997,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 78
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "79 - 1669 cases",
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
                                                95.709999999999994,
                                                100,
                                                50.759999999999998,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 1669
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "1670 - 45000 cases",
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
                                                100.18000000000001,
                                                100,
                                                45.100000000000001,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 43500
                    }
                ],
                "classBreakType": "GraduatedColor",
                "classificationMethod": "Quantile",
                "colorRamp": {
                    "type": "CIMMultipartColorRamp",
                    "colorRamps": [
                        {
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
                                "type": "CIMRGBColor",
                                "values": [
                                    38,
                                    115,
                                    0,
                                    100
                                ]
                            },
                            "interpolationSpace": "HSV",
                            "polarDirection": "Clockwise"
                        }
                    ],
                    "weights": [
                        1
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

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def makeSymb3(self, lyr_name):
        try:
            lyr = self.lyr_dict[lyr_name]
            definition = lyr.getDefinition('V2')

            definition.renderer = {
                "type": "CIMClassBreaksRenderer",
                "barrierWeight": "High",
                "breaks": [
                    {
                        "type": "CIMClassBreak",
                        "label": "1 - 4%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "name": "Group 1",
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 1,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                168,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "name": "Group 2",
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                175.31,
                                                212,
                                                161.5,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 0.044684005931150565
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "5 - 10%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "name": "Group 3",
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 1,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                168,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "name": "Group 4",
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                142.80000000000001,
                                                211.59999999999999,
                                                104.12,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 0.10000000000000001
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "11 - 20%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "name": "Group 5",
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 1,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                168,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "name": "Group 6",
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                150,
                                                0,
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
                        "label": "21 - 44%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "name": "Group 7",
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 1,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                168,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "name": "Group 8",
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                90,
                                                0,
                                                100
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        "upperBound": 0.4375
                    },
                    {
                        "type": "CIMClassBreak",
                        "label": "45 - 100%",
                        "patch": "Default",
                        "symbol": {
                            "type": "CIMSymbolReference",
                            "symbol": {
                                "type": "CIMPolygonSymbol",
                                "symbolLayers": [
                                    {
                                        "type": "CIMSolidStroke",
                                        "enable": True,
                                        "name": "Group 9",
                                        "capStyle": "Round",
                                        "joinStyle": "Round",
                                        "lineStyle3D": "Strip",
                                        "miterLimit": 10,
                                        "width": 1,
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                168,
                                                0,
                                                0,
                                                100
                                            ]
                                        }
                                    },
                                    {
                                        "type": "CIMSolidFill",
                                        "enable": True,
                                        "name": "Group 10",
                                        "color": {
                                            "type": "CIMRGBColor",
                                            "values": [
                                                0,
                                                50,
                                                0,
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
                "classificationMethod": "Quantile",
                "colorRamp": {
                    "type": "CIMMultipartColorRamp",
                    "colorSpace": {
                        "type": "CIMICCColorSpace",
                        "url": "Default RGB"
                    },
                    "colorRamps": [
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    247,
                                    252,
                                    253,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    229,
                                    245,
                                    249,
                                    100
                                ]
                            }
                        },
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    229,
                                    245,
                                    249,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    204,
                                    236,
                                    230,
                                    100
                                ]
                            }
                        },
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    204,
                                    236,
                                    230,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    153,
                                    216,
                                    201,
                                    100
                                ]
                            }
                        },
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    153,
                                    216,
                                    201,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    102,
                                    194,
                                    164,
                                    100
                                ]
                            }
                        },
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    102,
                                    194,
                                    164,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    65,
                                    174,
                                    118,
                                    100
                                ]
                            }
                        },
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    65,
                                    174,
                                    118,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    35,
                                    139,
                                    69,
                                    100
                                ]
                            }
                        },
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    35,
                                    139,
                                    69,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    0,
                                    109,
                                    44,
                                    100
                                ]
                            }
                        },
                        {
                            "type": "CIMLinearContinuousColorRamp",
                            "colorSpace": {
                                "type": "CIMICCColorSpace",
                                "url": "Default RGB"
                            },
                            "fromColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    0,
                                    109,
                                    44,
                                    100
                                ]
                            },
                            "toColor": {
                                "type": "CIMRGBColor",
                                "colorSpace": {
                                    "type": "CIMICCColorSpace",
                                    "url": "Default RGB"
                                },
                                "values": [
                                    0,
                                    68,
                                    27,
                                    100
                                ]
                            }
                        }
                    ],
                    "weights": [
                        0.125,
                        0.125,
                        0.125,
                        0.125,
                        0.125,
                        0.125,
                        0.125,
                        0.125
                    ]
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
                                "name": "Group 11",
                                "capStyle": "Round",
                                "joinStyle": "Round",
                                "lineStyle3D": "Strip",
                                "miterLimit": 10,
                                "width": 0.69999999999999996,
                                "color": {
                                    "type": "CIMRGBColor",
                                    "values": [
                                        255,
                                        0,
                                        0,
                                        100
                                    ]
                                }
                            },
                            {
                                "type": "CIMSolidFill",
                                "enable": True,
                                "name": "Group 12",
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
                                        255,
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
                },
                "useExclusionSymbol": False,
                "exclusionSymbolPatch": "Default",
                "visualVariables": [
                    {
                        "type": "CIMSizeVisualVariable",
                        "authoringInfo": {
                            "type": "CIMVisualVariableAuthoringInfo",
                            "maxSliderValue": 100,
                            "showLegend": True,
                            "heading": "Deaths rate."
                        },
                        "randomMax": 1,
                        "maxSize": 7,
                        "maxValue": 100,
                        "valueRepresentation": "Radius",
                        "variableType": "Graduated",
                        "valueShape": "Unknown",
                        "axis": "HeightAxis",
                        "target": "outline",
                        "normalizationType": "Nothing",
                        "valueExpressionInfo": {
                            "type": "CIMExpressionInfo",
                            "title": "Deaths rate.",
                            "expression": "($feature.Deaths/$feature.Confirmed)*100",
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
                    }
                ]
            }

            lyr.setDefinition(definition)
            self.active_map.addLayer(lyr, 'TOP')

            self.active_map.removeLayer(lyr)
            self.lyr_dict = {lyr.name.lower(): lyr for lyr in self.active_map.listLayers()}
        except Exception as e:
            arcpy.AddError(str(e))
        return

    def setTimeCursor(self, lyr_name, time_field):
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
                    "start": 1579737600000,
                    "end": 1583107200000,
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


app = wx.App()
Pivot(None, title='Pivot')
app.MainLoop()
