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
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Creates footprint polygons for each input line based on a least 
# cost corridor method and individual line thresholds.
#
# ---------------------------------------------------------------------------

import multiprocessing
import arcpy
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_LFP_output"
outWorkspace = ""
Corridor_Threshold_Field = ""
Maximum_distance_from_centerline = 0


def PathFile(path):
    return path[path.rfind("\\") + 1:]


def workLines(lineNo):
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

    # Temporary files
    fileSeg = outWorkspace + "\\FLM_LFP_Segment_" + str(lineNo) + ".shp"
    fileOrigin = outWorkspace + "\\FLM_LFP_Origin_" + str(lineNo) + ".shp"
    fileDestination = outWorkspace + "\\FLM_LFP_Destination_" + str(lineNo) + ".shp"
    fileBuffer = outWorkspace + "\\FLM_LFP_Buffer_" + str(lineNo) + ".shp"
    fileClip = outWorkspace + "\\FLM_LFP_Clip_" + str(lineNo) + ".tif"
    fileCostDa = outWorkspace + "\\FLM_LFP_CostDa_" + str(lineNo) + ".tif"
    fileCostDb = outWorkspace + "\\FLM_LFP_CostDb_" + str(lineNo) + ".tif"
    fileCorridor = outWorkspace + "\\FLM_LFP_Corridor_" + str(lineNo) + ".tif"
    fileCorridorMin = outWorkspace + "\\FLM_LFP_CorridorMin_" + str(lineNo) + ".tif"
    fileThreshold = outWorkspace + "\\FLM_LFP_Threshold_" + str(lineNo) + ".tif"
    fileExpand = outWorkspace + "\\FLM_LFP_Expand_" + str(lineNo) + ".tif"
    fileShrink = outWorkspace + "\\FLM_LFP_Shrink_" + str(lineNo) + ".tif"
    fileClean = outWorkspace + "\\FLM_LFP_Clean_" + str(lineNo) + ".tif"
    fileNull = outWorkspace + "\\FLM_LFP_Null_" + str(lineNo) + ".tif"
    fileFootprint = outWorkspace + "\\FLM_LFP_Footprint_" + str(lineNo) + ".shp"

    # When segment file is missing, just quit and log message
    # This segment will be recorded for later re-processing
    if not arcpy.Exists(fileSeg):
        print("{} doesn't exist, ignore.".format(fileSeg))
        return

    # Load segment list
    segment_list = []
    rows = arcpy.SearchCursor(fileSeg)
    shapeField = arcpy.Describe(fileSeg).ShapeFieldName
    for row in rows:
        feat = row.getValue(shapeField)  # creates a geometry object
        Corridor_Threshold = float(row.getValue(Corridor_Threshold_Field))
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
        arcpy.CreateFeatureclass_management(outWorkspace, PathFile(fileOrigin), "POINT", Centerline_Feature_Class, "DISABLED",
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
        arcpy.CreateFeatureclass_management(outWorkspace, PathFile(fileDestination), "POINT", Centerline_Feature_Class,
                                            "DISABLED", "DISABLED", Centerline_Feature_Class)
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
        arcpy.Buffer_analysis(fileSeg, fileBuffer, Maximum_distance_from_centerline, "FULL", "ROUND", "NONE", "", "PLANAR")
    except Exception as e:
        print("Create buffer for {} failed".format(fileSeg))
        print(e)
        return

    # Clip cost raster using buffer
    DescBuffer = arcpy.Describe(fileBuffer)
    SearchBox = str(DescBuffer.extent.XMin) + " " + str(DescBuffer.extent.YMin) + " " + str(
        DescBuffer.extent.XMax) + " " + str(DescBuffer.extent.YMax)
    arcpy.Clip_management(Cost_Raster, SearchBox, fileClip, fileBuffer, "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")

    # Process: Cost Distance
    arcpy.gp.CostDistance_sa(fileOrigin, fileClip, fileCostDa, "", "", "", "", "", "", "TO_SOURCE")
    arcpy.gp.CostDistance_sa(fileDestination, fileClip, fileCostDb, "", "", "", "", "", "", "TO_SOURCE")

    # Process: Corridor
    arcpy.gp.Corridor_sa(fileCostDa, fileCostDb, fileCorridor)

    # Calculate minimum value of corridor raster
    RasterCorridor = arcpy.Raster(fileCorridor)
    CorrMin = float(RasterCorridor.minimum)

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
    arcpy.RasterToPolygon_conversion(fileNull, fileFootprint, "SIMPLIFY", "VALUE", "SINGLE_OUTER_PART", "")

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


def HasField(fc, fi):
    fieldnames = [field.name for field in arcpy.ListFields(fc)]
    if fi in fieldnames:
        return True
    else:
        return False


def main(argv=None):
    # Setup script path and workspace folder
    workspaceName = "FLM_LFP_output"
    global outWorkspace
    outWorkspace = flmc.GetWorkspace(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_LFP_params.txt")

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

    if not HasField(Centerline_Feature_Class, Corridor_Threshold_Field):
        flmc.log("ERROR: There is no field named " + Corridor_Threshold_Field + " in the input lines")
        return False

    # Prepare input lines for multiprocessing
    numLines = flmc.SplitLines(Centerline_Feature_Class, outWorkspace, "LFP", ProcessSegments, Corridor_Threshold_Field)

    pool = multiprocessing.Pool(processes=flmc.GetCores())
    flmc.log("Multiprocessing line corridors...")
    pool.map(workLines, range(1, numLines + 1))
    pool.close()
    pool.join()
    flmc.logStep("Corridor multiprocessing")

    flmc.log("Merging footprint layers...")
    tempShapefiles = arcpy.ListFeatureClasses(wild_card='*Footprint*')
    fileMerge = outWorkspace + "\\FLM_LFP_Merge.shp"
    arcpy.Merge_management(tempShapefiles, fileMerge)
    arcpy.Dissolve_management(fileMerge, Output_Footprint)
    for shp in tempShapefiles:
        arcpy.Delete_management(shp)
    arcpy.Delete_management(fileMerge)
    flmc.logStep("Merging")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input("<Press any key to exit>")