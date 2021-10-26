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
# FLM_VertexOptimization.py
# Script Author: Richard Zeng
# Date: 2021-Oct-26
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Move line vertices to right seismic line courses
#
# ---------------------------------------------------------------------------
# System imports
import os
import multiprocessing

# ArcGIS imports
import arcpy
from arcpy.sa import *

# Local imports
arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_VO_output"


def PathFile(path):
    return path[path.rfind("\\") + 1:]


def groupIntersections():
    """
    Identify intersections of 2,3 or 4 lines and group them.
    Each group has all the end vertices, start(0) or end (-1) vertex and the line geometry
    """
    pass


def generateAnchorPtPairs():
    """
    Generate buffer of the intersection and extend lines to make them intersect with the buffer polygon.
    lines will be grouped along directions.
    """
    pass


def leastCostPath(pt_start, pt_end):
    """
    Calculate least cost path between two points
        pt_start: start point
        pt_end: end point
    """
    pass


def workLinesMem(segment_info):
    """
    New version of worklines. It uses memory workspace instead of shapefiles.
    The refactoring is to accelerate the processing speed.
    """

    # input verification
    if segment_info is None or len(segment_info) <= 1:
        print("Input segment is corrupted, ignore")

    # Temporary files
    outWorkspace = flmc.GetWorkspace(workspaceName)

    # read params from text file
    f = open(outWorkspace + "\\params.txt")
    Forest_Line_Feature_Class = f.readline().strip()
    Cost_Raster = f.readline().strip()
    Line_Processing_Radius = float(f.readline().strip())
    f.close()

    lineNo = segment_info[1]  # second element is the line No.
    outWorkspaceMem = r"memory"
    arcpy.env.workspace = r"memory"

    fileSeg = os.path.join(outWorkspaceMem, "FLM_VO_Segment_" + str(lineNo))
    fileOrigin = os.path.join(outWorkspaceMem, "FLM_VO_Origin_" + str(lineNo))
    fileDestination = os.path.join(outWorkspaceMem, "FLM_VO_Destination_" + str(lineNo))
    fileBuffer = os.path.join(outWorkspaceMem, "FLM_VO_Buffer_" + str(lineNo))
    fileClip = os.path.join(outWorkspaceMem, "FLM_VO_Clip_" + str(lineNo) + ".tif")
    fileCostDist = os.path.join(outWorkspaceMem, "FLM_VO_CostDist_" + str(lineNo) + ".tif")
    fileCostBack = os.path.join(outWorkspaceMem, "FLM_VO_CostBack_" + str(lineNo) + ".tif")
    fileCenterline = os.path.join(outWorkspaceMem, "FLM_VO_Centerline_" + str(lineNo))

    # Load segment list
    segment_list = []

    for line in segment_info[0]:
        for point in line:  # loops through every point in a line
            # loops through every vertex of every segment
            if point:  # adds all the vertices to segment_list, which creates an array
                segment_list.append(point)

    # Find origin and destination coordinates
    x1 = segment_list[0].X
    y1 = segment_list[0].Y
    x2 = segment_list[-1].X
    y2 = segment_list[-1].Y

    # Create segment feature class
    try:
        arcpy.CreateFeatureclass_management(outWorkspaceMem, os.path.basename(fileSeg), "POLYLINE",
                                            Forest_Line_Feature_Class, "DISABLED",
                                            "DISABLED", Forest_Line_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileSeg, ["SHAPE@"])
        cursor.insertRow([segment_info[0]])
        del cursor
    except Exception as e:
        print("Create feature class {} failed.".format(fileSeg))
        print(e)
        return

    # Create origin feature class
    # TODO: not in use, delete later
    try:
        arcpy.CreateFeatureclass_management(outWorkspaceMem, os.path.basename(fileOrigin), "POINT",
                                            Forest_Line_Feature_Class, "DISABLED",
                                            "DISABLED", Forest_Line_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileOrigin, ["SHAPE@XY"])
        xy = (float(x1), float(y1))
        cursor.insertRow([xy])
        del cursor
    except Exception as e:
        print("Creating origin feature class failed: at X, Y" + str(xy) + ".")
        print(e)
        return

    # Create destination feature class
    # TODO: not in use, delete later
    try:
        arcpy.CreateFeatureclass_management(outWorkspaceMem, os.path.basename(fileDestination), "POINT",
                                            Forest_Line_Feature_Class, "DISABLED",
                                            "DISABLED", Forest_Line_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileDestination, ["SHAPE@XY"])
        xy = (float(x2), float(y2))
        cursor.insertRow([xy])
        del cursor
    except Exception as e:
        print("Creating destination feature class failed: at X, Y" + str(xy) + ".")
        print(e)
        return

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
        # arcpy.gp.CostDistance_sa(fileOrigin, fileClip, fileCostDist, "", fileCostBack, "", "", "", "", "TO_SOURCE")
        fileCostDist = CostDistance(arcpy.PointGeometry(arcpy.Point(x1, y1)), fileClip, "", fileCostBack)
        # print("Cost distance file path: {}".format(fileCostDist))

        #arcpy.gp.CostPathAsPolyline_sa(fileDestination, fileCostDist,
        #                               fileCostBack, fileCenterline, "BEST_SINGLE", "")
        CostPathAsPolyline(arcpy.PointGeometry(arcpy.Point(x2, y2)), fileCostDist,
                           fileCostBack, fileCenterline, "BEST_SINGLE", "")

        # get centerline polyline out of memory feature class fileCenterline
        centerline = []
        with arcpy.da.SearchCursor(fileCenterline, ["SHAPE@"]) as cursor:
            for row in cursor:
                centerline.append(row[0])

    except Exception as e:
        print("Problem with line starting at X " + str(x1) + ", Y " + str(y1)
              + "; and ending at X " + str(x2) + ", Y " + str(y2) + ".")
        print(e)
        centerline = []
        return centerline

    # Clean temporary files
    arcpy.Delete_management(fileSeg)
    arcpy.Delete_management(fileOrigin)
    arcpy.Delete_management(fileDestination)
    arcpy.Delete_management(fileBuffer)
    arcpy.Delete_management(fileClip)
    arcpy.Delete_management(fileCostDist)
    arcpy.Delete_management(fileCostBack)

    # Return centerline
    print("Processing line {} done".format(fileSeg))
    return centerline


def main(argv=None):
    # Setup script path and workspace folder
    global workspaceName
    # workspaceName = "FLM_VO_output"

    global outWorkspace
    outWorkspace = flmc.SetupWorkspace(workspaceName)
    # outWorkspace = flmc.GetWorkspace(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_VO_params.txt")

    # Tool arguments
    global Forest_Line_Feature_Class
    Forest_Line_Feature_Class = args[0].rstrip()
    global Cost_Raster
    Cost_Raster = args[1].rstrip()
    global Line_Processing_Radius
    Line_Processing_Radius = args[2].rstrip()
    ProcessSegments = args[3].rstrip() == "True"
    Out_Centerline = args[4].rstrip()

    # write params to text file
    f = open(outWorkspace + "\\params.txt", "w")
    f.write(Forest_Line_Feature_Class + "\n")
    f.write(Cost_Raster + "\n")
    f.write(Line_Processing_Radius + "\n")
    f.close()

    # Prepare input lines for multiprocessing
    segment_all = flmc.SplitLines(Forest_Line_Feature_Class, outWorkspace, "CL", ProcessSegments)

    pool = multiprocessing.Pool(processes=flmc.GetCores())
    flmc.log("Multiprocessing center lines...")
    flmc.log("Using {} CPU cores".format(flmc.GetCores()))
    centerlines = pool.map(workLinesMem, segment_all)
    pool.close()
    pool.join()
    flmc.logStep("Center line multiprocessing done.")

    # No line generated, exit
    if len(centerlines) <= 0:
        print("No lines generated, exit")
        return

    # Create output centerline shapefile
    flmc.log("Create centerline shapefile...")
    try:
        arcpy.CreateFeatureclass_management(os.path.dirname(Out_Centerline), os.path.basename(Out_Centerline),
                                            "POLYLINE", Forest_Line_Feature_Class, "DISABLED",
                                            "DISABLED", Forest_Line_Feature_Class)
    except Exception as e:
        print("Create feature class {} failed.".format(Out_Centerline))
        print(e)
        return

    # Flatten centerlines which is a list of list
    flmc.log("Writing centerlines to shapefile...")
    # TODO: is this necessary? Since we need list of single line next
    #cl_list = [item for sublist in centerlines for item in sublist]
    cl_list = []
    for sublist in centerlines:
        if len(sublist) > 0:
            for item in sublist:
                cl_list.append(item)

    # arcpy.Merge_management(cl_list, Out_Centerline)
    with arcpy.da.InsertCursor(Out_Centerline, ["SHAPE@"]) as cursor:
        for line in cl_list:
            cursor.insertRow([line])

    # TODO: inspect CorridorTh
    if arcpy.Exists(Out_Centerline):
        arcpy.AddField_management(Out_Centerline, "CorridorTh", "DOUBLE")
        arcpy.CalculateField_management(Out_Centerline, "CorridorTh", "3")
    flmc.log("Centerlines shapefile done")

if __name__ == '__main__':
    main()