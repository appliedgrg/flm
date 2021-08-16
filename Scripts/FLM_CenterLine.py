#
#    Copyright (C) 2020  Applied Geospatial Research Group
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://gnu.org/licenses/gpl-3.0>.
#
# ---------------------------------------------------------------------------
#
# FLM_CenterLine.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Determines the least cost path between vertices of the input lines
#
# ---------------------------------------------------------------------------
import os
import multiprocessing
import arcpy
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_CL_output"


def PathFile(path):
    return path[path.rfind("\\") + 1:]


def workLines(lineNo):
    # Temporary files
    outWorkspace = flmc.GetWorkspace(workspaceName)

    # read params from text file
    f = open(outWorkspace + "\\params.txt")
    Forest_Line_Feature_Class = f.readline().strip()
    Cost_Raster = f.readline().strip()
    Line_Processing_Radius = f.readline().strip()
    f.close()

    fileSeg = outWorkspace + "\\FLM_CL_Segment_" + str(lineNo) + ".shp"
    fileOrigin = outWorkspace + "\\FLM_CL_Origin_" + str(lineNo) + ".shp"
    fileDestination = outWorkspace + "\\FLM_CL_Destination_" + str(lineNo) + ".shp"
    fileBuffer = outWorkspace + "\\FLM_CL_Buffer_" + str(lineNo) + ".shp"
    fileClip = outWorkspace + "\\FLM_CL_Clip_" + str(lineNo) + ".tif"
    fileCostDist = outWorkspace + "\\FLM_CL_CostDist_" + str(lineNo) + ".tif"
    fileCostBack = outWorkspace + "\\FLM_CL_CostBack_" + str(lineNo) + ".tif"
    fileCenterLine = outWorkspace + "\\FLM_CL_CenterLine_" + str(lineNo) + ".shp"

    # Load segment list
    segment_list = []
    rows = arcpy.SearchCursor(fileSeg)
    shapeField = arcpy.Describe(fileSeg).ShapeFieldName
    for row in rows:
        feat = row.getValue(shapeField)  # creates a geometry object
        segmentnum = 0
        for segment in feat:  # loops through every segment in a line
            # loops through every vertex of every segment
            for pnt in feat.getPart(
                    segmentnum):  # get.PArt returns an array of points for a particular part in the geometry
                if pnt:  # adds all the vertices to segment_list, which creates an array
                    segment_list.append(arcpy.Point(float(pnt.X), float(pnt.Y)))

            segmentnum += 1
    del rows

    # Find origin and destination coordinates
    x1 = segment_list[0].X
    y1 = segment_list[0].Y
    x2 = segment_list[-1].X
    y2 = segment_list[-1].Y

    # Create origin feature class
    try:
        arcpy.CreateFeatureclass_management(outWorkspace, PathFile(fileOrigin), "POINT", Forest_Line_Feature_Class,
                                            "DISABLED", "DISABLED", Forest_Line_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileOrigin, ["SHAPE@XY"])
        xy = (float(x1), float(y1))
        cursor.insertRow([xy])
        del cursor
    except Exception as e:
        print("Creating origin feature class failed: at X, Y" + str(xy) + ".")
        print(e)

    # Create destination feature class
    try:
        arcpy.CreateFeatureclass_management(outWorkspace, PathFile(fileDestination), "POINT", Forest_Line_Feature_Class,
                                            "DISABLED", "DISABLED", Forest_Line_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileDestination, ["SHAPE@XY"])
        xy = (float(x2), float(y2))
        cursor.insertRow([xy])
        del cursor
    except Exception as e:
        print("Creating destination feature class failed: at X, Y" + str(xy) + ".")
        print(e)

    try:
        # Buffer around line
        arcpy.Buffer_analysis(fileSeg, fileBuffer, Line_Processing_Radius, "FULL", "ROUND", "NONE", "", "PLANAR")

        # Clip cost raster using buffer
        DescBuffer = arcpy.Describe(fileBuffer)
        SearchBox = str(DescBuffer.extent.XMin) + " " + str(DescBuffer.extent.YMin) + " " + str(
            DescBuffer.extent.XMax) + " " + str(DescBuffer.extent.YMax)
        arcpy.Clip_management(Cost_Raster, SearchBox, fileClip, fileBuffer, "", "ClippingGeometry",
                              "NO_MAINTAIN_EXTENT")

        # Least cost path
        arcpy.gp.CostDistance_sa(fileOrigin, fileClip, fileCostDist, "", fileCostBack, "", "", "", "", "TO_SOURCE")
        arcpy.gp.CostPathAsPolyline_sa(fileDestination, fileCostDist, fileCostBack, fileCenterLine, "BEST_SINGLE", "")

    except Exception as e:
        print("Problem with line starting at X " + str(x1) + ", Y " + str(y1) + "; and ending at X " + str(
            x1) + ", Y " + str(y1) + ".")
        print(e)

    # Clean temporary files
    arcpy.Delete_management(fileSeg)
    arcpy.Delete_management(fileOrigin)
    arcpy.Delete_management(fileDestination)
    arcpy.Delete_management(fileBuffer)
    arcpy.Delete_management(fileClip)
    arcpy.Delete_management(fileCostDist)
    arcpy.Delete_management(fileCostBack)


def main(argv=None):
    # Setup script path and workspace folder
    global workspaceName
    workspaceName = "FLM_CL_output"

    global outWorkspace
    outWorkspace = flmc.SetupWorkspace(workspaceName)
    # outWorkspace = flmc.GetWorkspace(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_CL_params.txt")

    # Tool arguments
    global Forest_Line_Feature_Class
    Forest_Line_Feature_Class = args[0].rstrip()
    global Cost_Raster
    Cost_Raster = args[1].rstrip()
    global Line_Processing_Radius
    Line_Processing_Radius = args[2].rstrip()
    ProcessSegments = args[3].rstrip() == "True"
    Output_Centerline = args[4].rstrip()

    # write params to text file
    f = open(outWorkspace + "\\params.txt", "w")
    f.write(Forest_Line_Feature_Class + "\n")
    f.write(Cost_Raster + "\n")
    f.write(Line_Processing_Radius + "\n")
    f.close()

    # Prepare input lines for multiprocessing
    numLines = flmc.SplitLines(Forest_Line_Feature_Class, outWorkspace, "CL", ProcessSegments)

    pool = multiprocessing.Pool(processes=flmc.GetCores())
    flmc.log("Multiprocessing center lines...")
    pool.map(workLines, range(1, numLines + 1))
    pool.close()
    pool.join()

    flmc.logStep("Center line multiprocessing")

    flmc.log("Merging footprint layers...")
    tempShapefiles = arcpy.ListFeatureClasses()

    if tempShapefiles:
        arcpy.Merge_management(tempShapefiles, Output_Centerline)

    flmc.logStep("Merging")

    for shp in tempShapefiles:
        arcpy.Delete_management(shp)

    if os.path.exists(Output_Centerline):
        arcpy.AddField_management(Output_Centerline, "CorridorTh", "DOUBLE")
        arcpy.CalculateField_management(Output_Centerline, "CorridorTh", "3")


if __name__ == '__main__':
    main()
