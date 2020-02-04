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
import arcpy
import os
import sys
import time
import wx


class Pivot(wx.Frame):
    workspace = None  # default gdb path
    workfolder = None  # default gdb folder path
    aprx = arcpy.mp.ArcGISProject("CURRENT")  # current project
    active_map = None  # current map

    data_warehouse = []
    sizer = wx.GridBagSizer(0, 0)
    panel = None
    listFc = None
    listDm = None
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

    def __init__(self, parent, title):
        super(Pivot, self).__init__(parent, title=title, size=wx.Size(320, 500),
                                    style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):

        self.panel = wx.Panel(self)

        """List of Feature Classes"""
        text = wx.StaticText(self.panel, label="Feature Classes :")
        self.sizer.Add(text, pos=(0, 0), flag=wx.ALL, border=5)
        self.listFc = wx.ListCtrl(self.panel, -1, style=wx.LC_REPORT)
        self.listFc.InsertColumn(0, 'name', width=200)

        for fc in arcpy.ListFeatureClasses():
            self.listFc.InsertItem(self.inc, fc.title())
            self.inc += 1
            self.data_warehouse.append(arcpy.da.FeatureClassToNumPyArray(
                fc, [field.name for field in arcpy.ListFields(
                    os.path.join(str(self.workspace), fc))]))

        self.inc = 0

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnFeatureClick, self.listFc)
        self.sizer.Add(self.listFc, pos=(0, 1), span=(1, 2), border=5)

        """List of selected FC dimension's"""
        text = wx.StaticText(self.panel, label="Dimensions :")
        self.sizer.Add(text, pos=(1, 0), flag=wx.ALL, border=5)
        self.listDm = wx.ListCtrl(self.panel, -1, style=wx.LC_REPORT)
        self.listDm.InsertColumn(0, 'name', width=200)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnDimensionClick, self.listDm)
        self.sizer.Add(self.listDm, pos=(1, 1), span=(1, 2), border=5)

        """X axis"""
        self.sizer.Add(wx.StaticText(self.panel, label="X :"), pos=(2, 0), flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.sizer.Add(wx.StaticText(self.panel, label=""), pos=(2, 1), flag=wx.ALIGN_CENTER | wx.ALL, border=5)

        """Y axis"""
        self.sizer.Add(wx.StaticText(self.panel, label="Y :"), pos=(3, 0), flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.sizer.Add(wx.StaticText(self.panel, label=""), pos=(3, 1), flag=wx.ALIGN_CENTER | wx.ALL, border=5)

        """Z axis"""
        self.sizer.Add(wx.StaticText(self.panel, label="Z :"), pos=(4, 0), flag=wx.ALIGN_CENTER | wx.ALL, border=5)
        self.sizer.Add(wx.StaticText(self.panel, label=""), pos=(4, 1), flag=wx.ALIGN_CENTER | wx.ALL, border=5)

        """Run"""
        buttonRun = wx.Button(self.panel, label="Run")
        self.sizer.Add(buttonRun, pos=(5, 1), flag=wx.ALL, border=5)
        buttonRun.Bind(wx.EVT_BUTTON, self.OnRunClicked)

        """Pivot"""
        buttonPivot = wx.Button(self.panel, label="Pivot")
        self.sizer.Add(buttonPivot, pos=(5, 2), flag=wx.ALL, border=5)
        buttonPivot.Bind(wx.EVT_BUTTON, self.OnPivotClicked)

        self.panel.SetSizerAndFit(self.sizer)

    def OnFeatureClick(self, event):
        self.listDm.ClearAll()
        self.listDm.InsertColumn(0, 'name', width=200)
        for field in arcpy.ListFields(event.GetText()):
            if field.type == 'OID':
                continue
            self.listDm.InsertStringItem(0, field.name)

    def OnDimensionClick(self, event):
        if self.inc == 0:
            self.x = event.GetText()
            self.sizer.GetChildren()[5].GetWindow().SetLabelText(self.x)
            self.inc = 1
        elif self.inc == 1:
            self.y = event.GetText()
            self.sizer.GetChildren()[7].GetWindow().SetLabelText(self.y)
            self.inc = 2
        else:
            self.z = event.GetText()
            self.sizer.GetChildren()[9].GetWindow().SetLabelText(self.z)
            self.inc = 0

    def OnRunClicked(self, event):
        """ 'String'  ('SmallInteger'  'Integer')  ('Double' 'Single')  'Date' 'Geometry' """
        lyr = self.active_map.listLayers()[0]
        if self.x == 'Shape':
            if self.data_warehouse[self.listFc.GetFirstSelected()][0][self.y].dtype.type == np.str_:
                arcpy.AddMessage("(1)")

                """ Show Y as Label """
                definition = lyr.getDefinition('V2')
                definition.labelClasses[0].expression = '$feature.' + self.y
                definition.labelVisibility = True
                lyr.setDefinition(definition)

                """ Symbolize with Z"""
                lyrsmb = lyr.symbology
                lyrsmb.updateRenderer('GraduatedColorsRenderer')
                lyrsmb.renderer.classificationField = self.z
                lyrsmb.renderer.breakCount = 6
                lyrsmb.renderer.classificationMethod = 'NaturalBreaks'
                lyr.symbology = lyrsmb

        elif self.y == 'Shape':
            if self.data_warehouse[self.listFc.GetFirstSelected()][0][self.x].dtype.type == np.int32:
                arcpy.AddMessage("(3)")

                """ Show X as Label """
                definition = lyr.getDefinition('V2')
                definition.labelClasses[0].expression = '$feature.' + self.x
                definition.labelVisibility = True
                lyr.setDefinition(definition)

                """ Symbolize with Z"""
                lyrsmb = lyr.symbology
                lyrsmb.updateRenderer('UniqueValueRenderer')
                lyrsmb.renderer.classificationField = self.z
                lyrsmb.renderer.colorRamp = self.aprx.listColorRamps("Muted Pastels")[0]
                lyr.symbology = lyrsmb

        elif self.z == 'Shape':
            if self.data_warehouse[self.listFc.GetFirstSelected()][0][self.x].dtype.type == np.str_:
                arcpy.AddMessage("(2)")

                """ Symbolize with Z"""
                lyrsmb = lyr.symbology
                lyrsmb.updateRenderer('UniqueValueRenderer')
                lyrsmb.renderer.classificationField = self.z
                lyrsmb.renderer.colorRamp = self.aprx.listColorRamps("Basic Random")[0]
                lyr.symbology = lyrsmb

                """ Show X as Label """
                definition = lyr.getDefinition('V2')
                definition.labelClasses[0].expression = '$feature.' + self.x
                definition.labelVisibility = True
                lyr.setDefinition(definition)

                """Plot X and Y"""
                c = arcpy.Chart('Nombre d\'accidents par état.')
                c.type = 'bar'
                c.title = 'Nombre d\'accidents par état.'
                c.xAxis.field = self.x
                c.yAxis.field = self.y
                c.xAxis.title = self.x
                c.yAxis.title = self.y
                c.addToLayer(lyr)
        else:
            arcpy.AddMessage("This case is not supported")

    def OnPivotClicked(self, event):
        self.x, self.y, self.z = self.z, self.x, self.y

        self.sizer.GetChildren()[5].GetWindow().SetLabelText(self.x)
        self.sizer.GetChildren()[7].GetWindow().SetLabelText(self.y)
        self.sizer.GetChildren()[9].GetWindow().SetLabelText(self.z)
        self.OnRunClicked(event)


app = wx.App()
Pivot(None, title='Pivot')
app.MainLoop()

























# arcpy.AddMessage(self.data_warehouse[self.listFc.GetFirstSelected()][0][self.x].dtype.type)
# arcpy.AddMessage(self.data_warehouse[self.listFc.GetFirstSelected()][0][self.x])

# if self.data_warehouse[self.listFc.GetFirstSelected()][0][self.x] == np.typename
# arcpy.AddMessage(arcpy.ListFields(arcpy.ListFeatureClasses()[0])['OID'])
# arcpy.AddMessage(self.data_warehouse[self.listFc.GetFirstSelected()][:][self.x])

# X == self.sizer.GetChildren()[5].GetWindow().GetLabelText()
# Y == self.sizer.GetChildren()[7].GetWindow().GetLabelText()
# Z == self.sizer.GetChildren()[9].GetWindow().GetLabelText()

# yl = arcpy.ListFields(arcpy.ListFeatureClasses()[0])['OID']

# arcpy.AddMessage(arcpy.ListFields(arcpy.ListFeatureClasses()[0])[:])
# arcpy.AddMessage(yl)
# if yl.type == 'OID' or yl.type == 'Geometry':

# fig = plt.gcf()
# fig.show()
# fig.canvas.draw()
# x = data_warehouse[0][:][arcpy.ListFields(arcpy.ListFeatureClasses()[0])[6].name]
# # arcpy.AddMessage(arcpy.ListFields(arcpy.ListFeatureClasses()[0])[6].type)
# # arcpy.AddMessage(arcpy.ListFields(arcpy.ListFeatureClasses()[1]))
# plt.xlabel(arcpy.ListFields(arcpy.ListFeatureClasses()[0])[6].name)
# #   'String'  ('SmallInteger'  'Integer')  ('Double' 'Single')  'Date' 'Geometry'
# for i in range(len(arcpy.ListFields(arcpy.ListFeatureClasses()[0]))):
#     yl = arcpy.ListFields(arcpy.ListFeatureClasses()[0])[i]
#     arcpy.AddMessage(yl.type)
#     if yl.type == 'OID' or yl.type == 'Geometry':
#         continue
#     if i == len(arcpy.ListFields(arcpy.ListFeatureClasses()[0])) - 1:
#         arcpy.AddMessage("close")
#         plt.close()
#         break
#     plt.ylabel(yl.name)
#     y = data_warehouse[0][:][yl.name]
#     # compute something
#     plt.bar(x, y)  # plot something
#     # update canvas immediately
#     plt.pause(5)  # I ain't needed!!!
#     fig.clear()
#     fig.canvas.draw()

# lyr = active_map.listLayers()[0]
# lyrsmb = lyr.symbology
# lyrsmb.renderer.classificationField