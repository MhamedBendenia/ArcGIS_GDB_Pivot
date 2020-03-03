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
        self.axes = wx.StaticBitmap(self.panel, wx.ID_ANY,
                                    wx.Bitmap(str(pathlib.Path().absolute().joinpath(r"Scripts\Axes.png")),
                                              wx.BITMAP_TYPE_PNG), wx.DefaultPosition, (120, 120), 0)
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
            temp = self.zChoice.GetSelection()
            self.zChoice.SetSelection(self.yChoice.GetSelection())
            self.yChoice.SetSelection(temp)
            self.pivotRun()
            return
        elif 51 < x < 67 and 14 < y < 30:
            temp = self.xChoice.GetSelection()
            self.xChoice.SetSelection(self.zChoice.GetSelection())
            self.zChoice.SetSelection(temp)
            self.pivotRun()
            return
        elif 13 < x < 27 and 88 < y < 104:
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

                """Plot X(time) Y(point)"""
                self.stackPlot(data_name="covid_cases")

            else:
                arcpy.AddMessage("6")

                """Time cursor X"""
                self.setTimeCursor(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower(),
                                   time_field="Date")

                """Y symbolized with Y.fields[3]"""
                self.makeSymb(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower())

                """Plot X(states) Y(count_accidents)"""
                self.graphPlot(data_name="covid_cases")

        elif arcpy.da.Describe(self.yChoice.GetString(self.yChoice.GetSelection()).lower())["dataType"] == "TableView":
            if arcpy.Describe(self.xChoice.GetString(self.xChoice.GetSelection()).lower()).ShapeType == "Point":
                arcpy.AddMessage("4")

                """Z with Z.fields[0] as label"""
                self.makeLabel(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                               field_name="STATE_NAME")

                """Z symbolized with Z.fields[3]"""
                self.makeSymb(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower())

            else:
                arcpy.AddMessage("5")
        elif arcpy.da.Describe(self.zChoice.GetString(self.zChoice.GetSelection()).lower())["dataType"] == "TableView":
            if arcpy.Describe(self.xChoice.GetString(self.xChoice.GetSelection()).lower()).ShapeType == "Point":
                arcpy.AddMessage("2")
            else:
                arcpy.AddMessage("1")

        else:
            arcpy.AddWarning("This position is not supported.")

    def graphPlot(self, data_name):
        # graph plots
        df_temp = self.data_warehouse[data_name].groupby("Country_Region")["Confirmed",
                                                                           "Deaths", "Recovred"].max().reset_index()
        ind = np.arange(df_temp.Country_Region.count())  # the x locations for the groups

        f, ax = plt.subplots(figsize=(20, 5))

        p1 = ax.bar(ind - 0.20, df_temp.Confirmed, 0.20, color=(0.95, 0.62, 0.07, 1))
        p2 = ax.bar(ind, df_temp.Recovred, 0.20, color=(0.12, 0.52, 0.29, 1))
        p3 = ax.bar(ind + 0.20, df_temp.Deaths, 0.20, color=(1, 0, 0, 1))

        ax.set_title('Confirmed, Recovred and Deaths numbers by Country_Region.')
        plt.xticks(ind, df_temp.Country_Region)
        plt.xticks(rotation=90)
        ax.set_yscale('symlog')
        ax.legend((p1[0], p2[0], p3[0]), ('Confirmed', 'Recovred', 'Deaths'))

        plt.show()

    def stackPlot(self, data_name):
        df_temp = self.data_warehouse[data_name].groupby("Date")[
            "Confirmed", "Deaths", "Recovred"].max().reset_index()
        arcpy.AddMessage(df_temp)
        fig, ax = plt.subplots()
        plt.grid()
        ax.stackplot(df_temp.Date.values, df_temp.Deaths.values, df_temp.Recovred.values, df_temp.Confirmed.values,
                     labels=["Deaths", "Recovred", "Confirmed"],
                     colors=[(1, 0, 0, 1), (0.12, 0.52, 0.29, 1), (0.95, 0.62, 0.07, 1)])
        ax.legend(loc=2)
        plt.title("Confirmed, Deaths and Recovred cases stack by Date.")
        plt.xticks(rotation=70)
        plt.show()

    def makeLabel(self, lyr_name, field_name):
        lyr = self.lyr_dict[lyr_name]
        definition = lyr.getDefinition('V2')
        definition.labelClasses[0].expression = '$feature.' + field_name
        definition.labelClasses[0].maplexLabelPlacementProperties.enablePolygonFixedPosition = True
        definition.labelVisibility = True
        lyr.setDefinition(definition)
        return

    def makeSymb(self, lyr_name):
        try:
            lyr = self.lyr_dict[lyr_name]
            lyrsmb = lyr.symbology
            lyrsmb.renderer = {
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                                        "enable": true,
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
                    "zeroPad": true
                },
                "showInAscendingOrder": true,
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
                                "enable": true,
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
                                "enable": true,
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
                                "enable": true,
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
                                "enable": true,
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
                "useExclusionSymbol": false,
                "exclusionSymbolPatch": "Default"
            }
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

        except Exception as e:
            arcpy.AddError(str(e))
        return

    def timePlot(self, data_name, data_field, date_table_name, date_field, freq='M'):
        try:
            data = self.data_warehouse[data_name].set_index(data_field).join(self.data_warehouse[date_table_name]) \
                .set_index(date_field).groupby(pd.Grouper(freq=freq)).count()
        except Exception as e:
            arcpy.AddError(str(e))

        fig, axes = plt.subplots(figsize=(8, 4))
        axes.plot(data.index, data.values, '-')
        axes.set_xlabel("Time")
        axes.set_ylabel(data_name)
        fig.autofmt_xdate()
        plt.show()
        return

    def dataPlot(self, x_data_name, x_data_field, y_data_name, y_data_field):
        try:
            data = self.data_warehouse[x_data_name].merge(self.data_warehouse[y_data_name],
                                                          left_index=True,
                                                          right_on=y_data_field,
                                                          how='outer').groupby([x_data_field]).count()[y_data_field]
        except Exception as e:
            arcpy.AddError(str(e))

        fig, axes = plt.subplots(figsize=(8, 4))
        axes.bar(data.index, data.values)
        axes.set_xlabel(x_data_name)
        axes.set_ylabel(y_data_name)
        plt.show()
        return


app = wx.App()
Pivot(None, title='Pivot')
app.MainLoop()
