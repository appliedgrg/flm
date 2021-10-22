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
# FLM_LineFootprint.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
# Refactor to use memory workspace to speedup processing
# Richard Zeng
# Date: 2021-August
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Creates footprint polygons for each input line based on a least 
# cost corridor method and individual line thresholds.
#
# ---------------------------------------------------------------------------

# System imports
import os
import multiprocessing

# ArcGIS imports
import arcpy
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_PT_output"
outWorkspace = ""
Corridor_Threshold_Field = ""
Maximum_distance_from_centerline = 0


def PathFile(path):
    return path[path.rfind("\\") + 1:]


def workLinesMem(segment_info):
    """
    New version of worklines. It uses memory workspace instead of shapefiles.
    The refactoring is to accelerate the processing speed.
    """
    # input verification
    if segment_info is None or len(segment_info) <= 1:
        print("Input segment is corrupted, ignore")

    # read params from text file
    outWorkspace = flmc.GetWorkspace(workspaceName)
    f = open(outWorkspace + "\\params.txt")
    outWorkspace = f.readline().strip()
    Centerline_Feature_Class = f.readline().strip()
    Canopy_Raster = f.readline().strip()
    Cost_Raster = f.readline().strip()
    Corridor_Threshold_Field = f.readline().strip()
    Maximum_distance_from_centerline = float(f.readline().strip())
    Expand_And_Shrink_Cell_Range = f.readline().strip()
    f.close()

    # TODO: this is constant, but need to be investigated.
    Corridor_Threshold = 3
    lineNo = segment_info[1]  # second element is the line No.
    outWorkspaceMem = r"memory"

    # Temporary files
    fileSeg = os.path.join(outWorkspaceMem, "FLM_PT_Segment_" + str(lineNo))
    fileOrigin = os.path.join(outWorkspaceMem, "FLM_PT_Origin_" + str(lineNo))
    fileDestination = os.path.join(outWorkspaceMem, "FLM_PT_Destination_" + str(lineNo))
    fileBuffer = os.path.join(outWorkspaceMem, "FLM_PT_Buffer_" + str(lineNo))
    fileClip = os.path.join(outWorkspaceMem, "FLM_PT_Clip_" + str(lineNo) + ".tif")
    fileCostDa = os.path.join(outWorkspaceMem, "FLM_PT_CostDa_" + str(lineNo) + ".tif")
    fileCostDb = os.path.join(outWorkspaceMem, "FLM_PT_CostDb_" + str(lineNo) + ".tif")
    fileCorridor = os.path.join(outWorkspaceMem, "FLM_PT_Corridor_" + str(lineNo) + ".tif")
    fileCorridorMin = os.path.join(outWorkspaceMem, "FLM_PT_CorridorMin_" + str(lineNo) + ".tif")
    fileThreshold = os.path.join(outWorkspaceMem, "FLM_PT_Threshold_" + str(lineNo) + ".tif")
    fileExpand = os.path.join(outWorkspaceMem, "FLM_PT_Expand_" + str(lineNo) + ".tif")
    fileShrink = os.path.join(outWorkspaceMem, "FLM_PT_Shrink_" + str(lineNo) + ".tif")
    fileClean = os.path.join(outWorkspaceMem, "FLM_PT_Clean_" + str(lineNo) + ".tif")
    fileNull = os.path.join(outWorkspaceMem, "FLM_PT_Null_" + str(lineNo) + ".tif")

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
                                            Centerline_Feature_Class, "DISABLED",
                                            "DISABLED", Centerline_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileSeg, ["SHAPE@"])
        cursor.insertRow([segment_info[0]])
        del cursor
    except Exception as e:
        print("Create feature class {} failed.".format(fileSeg))
        print(e)
        return

    # Create origin feature class
    try:
        arcpy.CreateFeatureclass_management(outWorkspaceMem, os.path.basename(fileOrigin), "POINT",
                                            Centerline_Feature_Class, "DISABLED",
                                            "DISABLED", Centerline_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileOrigin, ["SHAPE@XY"])
        xy = (float(x1), float(y1))
        cursor.insertRow([xy])
        del cursor
    except Exception as e:
        print("Create feature class {} failed.".format(fileOrigin))
        print(e)
        return

    # Create destination feature class
    try:
        arcpy.CreateFeatureclass_management(outWorkspaceMem, os.path.basename(fileDestination), "POINT",
                                            Centerline_Feature_Class, "DISABLED",
                                            "DISABLED", Centerline_Feature_Class)
        cursor = arcpy.da.InsertCursor(fileDestination, ["SHAPE@XY"])
        xy = (float(x2), float(y2))
        cursor.insertRow([xy])
        del cursor
    except Exception as e:
        print("Create feature class {} failed.".format(fileDestination))
        print(e)
        return

    # Buffer around line
    try:
        arcpy.Buffer_analysis(fileSeg, fileBuffer, Maximum_distance_from_centerline,
                              "FULL", "ROUND", "NONE", "", "PLANAR")
    except Exception as e:
        print("Create buffer for {} failed".format(fileSeg))
        print(e)
        return

    # Clip cost raster using buffer
    DescBuffer = arcpy.Describe(fileBuffer)
    SearchBox = str(DescBuffer.extent.XMin) + " " + str(DescBuffer.extent.YMin) + " " + str(
        DescBuffer.extent.XMax) + " " + str(DescBuffer.extent.YMax)
    arcpy.Clip_management(Cost_Raster, SearchBox, fileClip, fileBuffer, "",
                          "ClippingGeometry", "NO_MAINTAIN_EXTENT")

    try:
        # Process: Cost Distance
        arcpy.gp.CostDistance_sa(fileOrigin, fileClip, fileCostDa, "", "", "", "", "", "", "TO_SOURCE")
        arcpy.gp.CostDistance_sa(fileDestination, fileClip, fileCostDb, "", "", "", "", "", "", "TO_SOURCE")

        # Process: Corridor
        arcpy.gp.Corridor_sa(fileCostDa, fileCostDb, fileCorridor)
    except Exception as e:
        print(e)

    footprint = []

    # Calculate minimum value of corridor raster
    try:
        RasterCorridor = arcpy.Raster(fileCorridor)

        if not RasterCorridor.minimum is None:
            CorrMin = float(RasterCorridor.minimum)
        else:
            print("Line segment {} error: RasterCorridor.minimum is None", lineNo)
            CorrMin = 0

        # Set minimum as zero and save minimum file
        RasterCorridor = ((RasterCorridor - CorrMin) > Corridor_Threshold)
        RasterCorridor.save(fileCorridorMin)

        # Process: Stamp CC and Max Line Width
        RasterClass = SetNull(IsNull(Raster(fileCorridorMin)), (Raster(fileCorridorMin) + (Raster(Canopy_Raster) >= 1)) > 0)
        RasterClass.save(fileThreshold)
        del RasterCorridor, RasterClass

        if (int(Expand_And_Shrink_Cell_Range) > 0):
            # Process: Expand
            arcpy.gp.Expand_sa(fileThreshold, fileExpand, Expand_And_Shrink_Cell_Range, "1")

            # Process: Shrink
            arcpy.gp.Shrink_sa(fileExpand, fileShrink, Expand_And_Shrink_Cell_Range, "1")
        else:
            fileShrink = fileThreshold

        # Process: Boundary Clean
        arcpy.gp.BoundaryClean_sa(fileShrink, fileClean, "ASCEND", "ONE_WAY")
        # arcpy.gp.BoundaryClean_sa(fileShrink, fileClean, "NO_SORT", "ONE_WAY")  # This is original code

        # Process: Set Null
        arcpy.gp.SetNull_sa(fileClean, "1", fileNull, "VALUE > 0")

        # Process: Raster to Polygon
        footprint = arcpy.RasterToPolygon_conversion(fileNull, arcpy.Geometry(),
                                                     "SIMPLIFY", "VALUE", "SINGLE_OUTER_PART", "")
    except Exception as e:
        print(e)

    flmc.log("Processing line {} done".format(fileSeg))

    # Clean temporary files
    try:
        arcpy.Delete_management(fileSeg)
        arcpy.Delete_management(fileOrigin)
        arcpy.Delete_management(fileDestination)
        arcpy.Delete_management(fileBuffer)
        arcpy.Delete_management(fileClip)
        arcpy.Delete_management(fileCostDa)
        arcpy.Delete_management(fileCostDb)
        arcpy.Delete_management(fileThreshold)
        arcpy.Delete_management(fileCorridor)
        arcpy.Delete_management(fileCorridorMin)
        arcpy.Delete_management(fileExpand)
        arcpy.Delete_management(fileShrink)
        arcpy.Delete_management(fileClean)
        arcpy.Delete_management(fileNull)
    except Exception as e:
        print("Line Footprint: Deleting temporary file failed. Inspect later.")

    return footprint  # list of polygons

def HasField(fc, fi):
    fieldnames = [field.name for field in arcpy.ListFields(fc)]
    if fi in fieldnames:
        return True
    else:
        return False


def main(argv=None):
    # Setup script path and workspace folder
    workspaceName = "FLM_PT_output"
    global outWorkspace
    outWorkspace = flmc.GetWorkspace(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_PT_params.txt")

    # Tool arguments
    global Centerline_Feature_Class
    Centerline_Feature_Class = args[0].rstrip()
    global Canopy_Raster
    Canopy_Raster = args[1].rstrip()
    global Cost_Raster
    Cost_Raster = args[2].rstrip()
    global Corridor_Threshold_Field
    Corridor_Threshold_Field = args[3].rstrip()
    global Maximum_distance_from_centerline
    Maximum_distance_from_centerline = float(args[4].rstrip()) / 2.0
    global Expand_And_Shrink_Cell_Range
    Expand_And_Shrink_Cell_Range = args[5].rstrip()
    global ProcessSegments
    ProcessSegments = args[6].rstrip() == "True"
    global Output_Footprint
    Output_Footprint = args[7].rstrip()
    outWorkspace = flmc.SetupWorkspace(workspaceName)

    # write params to text file
    f = open(outWorkspace + "\\params.txt", "w")
    f.write(outWorkspace + "\n")
    f.write(Centerline_Feature_Class + "\n")
    f.write(Canopy_Raster + "\n")
    f.write(Cost_Raster + "\n")
    f.write(Corridor_Threshold_Field + "\n")
    f.write(str(Maximum_distance_from_centerline) + "\n")
    f.write(Expand_And_Shrink_Cell_Range + "\n")
    f.close()

    # TODO: this code block is not necessary
    if not HasField(Centerline_Feature_Class, Corridor_Threshold_Field):
        flmc.log("ERROR: There is no field named " + Corridor_Threshold_Field + " in the input lines")
        return False

    # Prepare input lines for multiprocessing
    segment_all = flmc.SplitLines(Centerline_Feature_Class, outWorkspace,
                                  "LFP", ProcessSegments, Corridor_Threshold_Field)

    # TODO: inspect how GetCores works. Make sure it uses all the CPU cores
    pool = multiprocessing.Pool(processes=flmc.GetCores())
    flmc.log("Multiprocessing line corridors...")
    flmc.log("Using {} CPU cores".format(flmc.GetCores()))

    footprints = pool.map(workLinesMem, segment_all)  # new version of memory based processing
    pool.close()
    pool.join()
    flmc.logStep("Corridor multiprocessing")

    flmc.log("Merging footprints...")
    try:
        # Flatten footprints which is a list of list
        ft_list = [item for sublist in footprints for item in sublist]

        fileMerge = outWorkspace + "\\FLM_PT_Merge.shp"
        arcpy.Merge_management(ft_list, fileMerge)
        arcpy.Dissolve_management(fileMerge, Output_Footprint)
        # arcpy.Delete_management(fileMerge)
    except Exception as e:
        print("e")

    flmc.logStep("Footprints merged.")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input("<Press any key to exit>")
