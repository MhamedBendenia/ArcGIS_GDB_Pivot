"""
-------------------------------------------------------------------------
    Tool:               Pivot
    Source Name:        Pivot.py
    Author:             M'hamed Bendenia.
-------------------------------------------------------------------------
"""

from random import randrange
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import arcpy
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
            self.xChoice.Append(fc.title())
            self.yChoice.Append(fc.title())
            self.zChoice.Append(fc.title())
            self.data_warehouse[fc.title().lower()] = pd.DataFrame(data=arcpy.da.FeatureClassToNumPyArray(
                fc, [field.name for field in arcpy.ListFields(os.path.join(str(self.workspace), fc))[2:]]),
                index=arcpy.da.FeatureClassToNumPyArray(fc, ['OBJECTID'])[:]['OBJECTID'],
                columns=[field.name for field in arcpy.ListFields(os.path.join(str(self.workspace), fc))[2:]])

        """Filling the DW and the lists by tables"""
        for tb in arcpy.ListTables():
            if tb.title() == "Fact":
                self.Fact = pd.DataFrame(data=arcpy.da.TableToNumPyArray(
                    tb, [field.name for field in arcpy.ListFields(os.path.join(str(self.workspace), tb))[1:]]),
                    index=arcpy.da.FeatureClassToNumPyArray(tb, ['OBJECTID'])[:]['OBJECTID'],
                    columns=[field.name for field in arcpy.ListFields(os.path.join(str(self.workspace), tb))[1:]])
                continue
            self.xChoice.Append(tb.title())
            self.yChoice.Append(tb.title())
            self.zChoice.Append(tb.title())
            self.data_warehouse[tb.title().lower()] = pd.DataFrame(data=arcpy.da.TableToNumPyArray(
                tb, [field.name for field in arcpy.ListFields(os.path.join(str(self.workspace), tb))[1:]]),
                index=arcpy.da.FeatureClassToNumPyArray(tb, ['OBJECTID'])[:]['OBJECTID'],
                columns=[field.name for field in arcpy.ListFields(os.path.join(str(self.workspace), tb))[1:]])

        # y = self.data_warehouse["Us_Accidents_Xy"].loc[lambda df: df['Severity'] == 2, :].index
        # x = self.Fact.loc[lambda df: df['accident_id'].isin(y), "state_id"]
        # arcpy.AddMessage(self.data_warehouse[0].loc[lambda df: df['Severity'] == 2, :].index)
        # arcpy.AddMessage(self.data_warehouse[0].loc[lambda df: df['Severity'] == 2, :])
        # arcpy.AddMessage(x.groupby("state_id"))

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
        if arcpy.da.Describe(self.xChoice.GetString(self.xChoice.GetSelection()).lower())["dataType"] == "TableView":
            if arcpy.Describe(self.yChoice.GetString(self.yChoice.GetSelection()).lower()).ShapeType == "Point":
                arcpy.AddMessage("3")

                """Z with Z.fields[0] as label"""
                self.makeLabel(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(), field_pos=0)

                """Z symbolized with Z.fields[3]"""
                self.makeSymb(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                              field_pos=3,
                              render="GraduatedColorsRenderer")

                """Plot X(time) Y(point)"""
                self.timePlot(data_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower(),
                              data_field="Date_id",
                              date_table_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower(),
                              date_field="Date",
                              freq='M')
            else:
                arcpy.AddMessage("6")
                """Time cursor X"""

                """Plot X(time) Y(point)"""
                self.dataPlot(x_data_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower(),
                              x_data_field="Date_id",
                              y_data_name=self.yChoice.GetString(self.yChoice.GetSelection()).lower(),
                              y_data_field="Date_id")

        elif arcpy.da.Describe(self.yChoice.GetString(self.yChoice.GetSelection()).lower())["dataType"] == "TableView":
            if arcpy.Describe(self.xChoice.GetString(self.xChoice.GetSelection()).lower()).ShapeType == "Point":
                arcpy.AddMessage("4")

                """Z with Z.fields[0] as label"""
                self.makeLabel(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(), field_pos=0)

                """Z symbolized with Z.fields[3]"""
                self.makeSymb(lyr_name=self.zChoice.GetString(self.zChoice.GetSelection()).lower(),
                              field_pos=3,
                              render="UniqueValueRenderer")

            else:
                arcpy.AddMessage("5")
        elif arcpy.da.Describe(self.zChoice.GetString(self.zChoice.GetSelection()).lower())["dataType"] == "TableView":
            if arcpy.Describe(self.xChoice.GetString(self.xChoice.GetSelection()).lower()).ShapeType == "Point":
                arcpy.AddMessage("2")
            else:
                arcpy.AddMessage("1")

                """X with X.fields[3] as label"""
                self.makeLabel(lyr_name=self.xChoice.GetString(self.xChoice.GetSelection()).lower(), field_pos=3)
        else:
            arcpy.AddWarning("This position is not supported.")

        #
        # self.xChoice.GetSelection()
        # if self.x == 'Shape':
        #     if self.data_warehouse[self.listFc.GetFirstSelected()][0][self.y].dtype.type == np.str_:
        #
        #         """ Show Y as Label """
        #         definition = lyr.getDefinition('V2')
        #         definition.labelClasses[0].expression = '$feature.' + self.y
        #         definition.labelVisibility = True
        #         lyr.setDefinition(definition)
        #
        #         """ Symbolize with Z"""
        #         lyrsmb = lyr.symbology
        #         lyrsmb.updateRenderer('GraduatedColorsRenderer')
        #         lyrsmb.renderer.classificationField = self.z
        #         lyrsmb.renderer.breakCount = 6
        #         lyrsmb.renderer.classificationMethod = 'NaturalBreaks'
        #         lyr.symbology = lyrsmb
        #
        # elif self.y == 'Shape':
        #     if self.data_warehouse[self.listFc.GetFirstSelected()][0][self.x].dtype.type == np.int32:
        #         arcpy.AddMessage("(3)")
        #
        #         """ Show X as Label """
        #         definition = lyr.getDefinition('V2')
        #         definition.labelClasses[0].expression = '$feature.' + self.x
        #         definition.labelVisibility = True
        #         lyr.setDefinition(definition)
        #
        #         """ Symbolize with Z"""
        #         lyrsmb = lyr.symbology
        #         lyrsmb.updateRenderer('UniqueValueRenderer')
        #         lyrsmb.renderer.classificationField = self.z
        #         lyrsmb.renderer.colorRamp = self.aprx.listColorRamps("Muted Pastels")[0]
        #         lyr.symbology = lyrsmb
        #
        # elif self.z == 'Shape':
        #     if self.data_warehouse[self.listFc.GetFirstSelected()][0][self.x].dtype.type == np.str_:
        #         arcpy.AddMessage("(2)")
        #
        #         """ Symbolize with Z"""
        #         lyrsmb = lyr.symbology
        #         lyrsmb.updateRenderer('UniqueValueRenderer')
        #         lyrsmb.renderer.classificationField = self.z
        #         lyrsmb.renderer.colorRamp = self.aprx.listColorRamps("Basic Random")[0]
        #         lyr.symbology = lyrsmb
        #
        #         """ Show X as Label """
        #         definition = lyr.getDefinition('V2')
        #         definition.labelClasses[0].expression = '$feature.' + self.x
        #         definition.labelVisibility = True
        #         lyr.setDefinition(definition)
        #
        #         """Plot X and Y"""
        #         c = arcpy.Chart('Nombre d\'accidents par état.')
        #         c.type = 'bar'
        #         c.title = 'Nombre d\'accidents par état.'
        #         c.xAxis.field = self.x
        #         c.yAxis.field = self.y
        #         c.xAxis.title = self.x
        #         c.yAxis.title = self.y
        #         c.addToLayer(lyr)
        # else:
        #     arcpy.AddMessage("This case is not supported")
        #

    def makeLabel(self, lyr_name, field_pos):
        lyr = self.lyr_dict[lyr_name]
        definition = lyr.getDefinition('V2')
        definition.labelClasses[0].expression = '$feature.' + \
                                                self.data_warehouse[lyr.name.lower()].columns.array[field_pos]
        definition.labelVisibility = True
        lyr.setDefinition(definition)
        return

    def makeSymb(self, lyr_name, field_pos=None, render='SimpleRenderer'):
        # 'UniqueValueRenderer'  'GraduatedColorsRenderer' 'SimpleRenderer'
        lyr = self.lyr_dict[lyr_name]
        lyrsmb = lyr.symbology
        lyrsmb.updateRenderer(render)
        lyrsmb.renderer.classificationField = self.data_warehouse[lyr.name.lower()].columns.array[field_pos]
        if render == 'GraduatedColorsRenderer':
            lyrsmb.renderer.classificationMethod = 'NaturalBreaks'
        else:
            lyrsmb.renderer.colorRamp = self.aprx.listColorRamps("Basic Random")[0]
        lyr.symbology = lyrsmb
        return

    def timePlot(self, data_name=None, data_field=None, date_table_name=None, date_field=None, freq='M'):
        data = self.data_warehouse[data_name].set_index(data_field).join(self.data_warehouse[date_table_name]) \
            .set_index(date_field).groupby(pd.Grouper(freq=freq)).count()
        arcpy.AddMessage(data)
        fig, axes = plt.subplots(figsize=(8, 4))
        axes.plot(data.index, data.values, '-')
        axes.set_xlabel("Time")
        axes.set_ylabel(data_name)
        fig.autofmt_xdate()
        plt.show()
        return

    def dataPlot(self, x_data_name=None, x_data_field=None, y_data_name=None, y_data_field=None):
-------------------------------------------------------------------------------------------------------------------------------------------
        return



app = wx.App()
Pivot(None, title='Pivot')
app.MainLoop()


# FindHotSpots(point_layer, output_name, {bin_size}, {neighborhood_size})
#
# arcpy.Describe('us_states').ShapeType
# 'Polygon'
# list(d.keys())[0]