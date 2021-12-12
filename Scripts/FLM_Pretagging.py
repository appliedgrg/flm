#
#    Copyright (C) 2021  Applied Geospatial Research Group
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
# FLM_Pretagging.py
# Script Author: Richard Zeng
# Date: 2021-Oct-25
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Tag lines using the line and LiDAR age or
# by checking the raster values in line footprint.
#
# ---------------------------------------------------------------------------

# System imports
import os
import multiprocessing
import math

from statistics import *

# ArcGIS imports
import arcpy
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_PT_output"
outWorkspace = ""
Maximum_distance_from_centerline = 32
ProcessSegments = False  # keep whole line by default

def PathFile(path):
    return path[path.rfind("\\") + 1:]

def retrievePolygons(polygon_shpfile):
    """
    Retrieve all polygon geometries from shpaefile
    """
    fields = ["SHAPE@", "Year"]
    polygons = []
    with arcpy.da.SearchCursor(polygon_shpfile, fields) as cursor:
        for row in cursor:
            if row[1] > 0:
                polygons.append(row)

    return polygons

def existenceByLiDARYear(line_info):
    line = line_info[0]
    polygons = line_info[3]
    years = []
    for polygon in polygons:
        if polygon[0].crosses(line) or polygon[0].contains(line):
            years.append(polygon[1])

    if len(years) > 0 and line_info[2]["YEAR"] > 0:
        if max(years) > line_info[2]["YEAR"]:
            return True

    return False


def getStats(point_values):
    if len(point_values) <= 1:
        return -9999.0, -9999.0, -9999.0, -9999.0

    pt_mean = mean(point_values)
    pt_median = median(point_values)
    pt_variance = variance(point_values)
    pt_stdev = stdev(point_values)

    return pt_mean, pt_median, pt_variance, pt_stdev

def tagLine(footprint_list, in_chm, in_line):
    if not footprint_list or len(footprint_list) == 0:
        return (False, -9999.0, -9999, -9999, -9999, -9999, -9999, -9999, -9999)

    footprint = footprint_list[0]
    outWorkspaceMem = r"memory"
    lineNo = in_line[1]
    distance_from_centerline = 5  # buffer 5 meters

    # Temporary files
    fileBuffer = os.path.join(outWorkspaceMem, "FLM_PT_Buffer_" + str(lineNo))
    fileExtraction = os.path.join(outWorkspaceMem, "FLM_PT_Extract_" + str(lineNo))
    fileNeighborExtraction = os.path.join(outWorkspaceMem, "FLM_PT_Extract_Neighbor_" + str(lineNo))

    # arcpy.Buffer_analysis(footprint, fileBuffer, distance_from_centerline,
    #                       "FULL", "ROUND", "NONE", "", "PLANAR")
    footprint_buffer = footprint.buffer(distance_from_centerline)
    footprint_neighbor = footprint_buffer.difference(footprint)

    extraction_raster = None
    extraction_raster_buffer = None
    try:
        # Extract raster values
        extraction_raster = ExtractByMask(in_chm, footprint)
        extraction_raster_neighbor = ExtractByMask(in_chm, footprint_neighbor)

        arcpy.RasterToPoint_conversion(extraction_raster, fileExtraction)
        arcpy.RasterToPoint_conversion(extraction_raster_neighbor, fileNeighborExtraction)
    except Exception as e:
        print(e)

    extract_values = []
    extract_neighbor_values = []

    try:
        with arcpy.da.SearchCursor(fileExtraction, ["grid_code"]) as cursor:
            for row in cursor:
                extract_values.append(row[0])

        with arcpy.da.SearchCursor(fileNeighborExtraction, ["grid_code"]) as cursor:
            for row in cursor:
                extract_neighbor_values.append(row[0])
    except Exception as e:
        print(e)

    # Get raster value stats for footprint and neighbor area
    pt_stats = getStats(extract_values)
    pt_stats_buffer = getStats(extract_neighbor_values)

    # Remove temporary rasters
    try:
        if extraction_raster:
            arcpy.Delete_management(extraction_raster)
        if extraction_raster_buffer:
            arcpy.Delete_management(extraction_raster_buffer)
        arcpy.Delete_management(fileExtraction)
        arcpy.Delete_management(fileNeighborExtraction)
    except Exception as e:
        print(e)

    # determine if line status: confirmed, unconfirmed and invisible
    def validStats(stats):
        """Check if there is value in list stats is not close to flmc.EPSILON
        If there is at least one such value, return Ture,
        or return False, which means list like [-9999, -9999, ..., -9999]"""

        isValid = False
        for i in stats:
            if not math.isclose(i, flmc.NO_DATA, rel_tol=flmc.EPSILON):
                isValid = True

        return isValid

    # TODO: need more sophisticated rules to determine line status
    if pt_stats and pt_stats[0] < 0.5:
        lineExistence = "confirmed"
    elif not validStats(pt_stats):
        lineExistence = "unconfirmed"
    else:
        lineExistence = "invisible"

    return [lineExistence] + list(pt_stats) + list(pt_stats_buffer)


def workLinesMem(segment_info):
    """
    New version of worklines. It uses memory workspace instead of shapefiles.
    The refactoring is to accelerate the processing speed.
    """
    failed_line = (segment_info[0], ("False", -9999.0, -9999.0, -9999.0, -9999.0, -9999.0, -9999.0, -9999.0, -9999.0), segment_info[2])
    # input verification
    if segment_info is None or len(segment_info) <= 1:
        print("Input segment is corrupted, ignore")
        return failed_line

    # read params from text file
    outWorkspace = flmc.GetWorkspace(workspaceName)
    f = open(outWorkspace + "\\params.txt")
    outWorkspace = f.readline().strip()
    Centerline_Feature_Class = f.readline().strip()
    In_CHM = f.readline().strip()
    Canopy_Raster = f.readline().strip()
    Cost_Raster = f.readline().strip()
    In_Lidar_Year = f.readline().strip()
    Maximum_distance_from_centerline = float(f.readline().strip())
    Out_Tagged_Line = f.readline().strip()
    f.close()

    # Determine line existence by LiDAR year
    line_exist = [False, -9999.0, -9999, -9999, -9999, -9999, -9999, -9999, -9999]

    if existenceByLiDARYear(segment_info):
        line_exist[0] = True
        return segment_info[0], line_exist, segment_info[2]

    # TODO: remove this parameter
    Expand_And_Shrink_Cell_Range = 0

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
        return failed_line

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
        return failed_line

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
        return failed_line

    # Buffer around line
    try:
        arcpy.Buffer_analysis(segment_info[0], fileBuffer, Maximum_distance_from_centerline,
                              "FULL", "ROUND", "NONE", "", "PLANAR")
    except Exception as e:
        print("Create buffer for {} failed".format(lineNo))
        print(e)
        return failed_line

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
        return failed_line

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
        return failed_line

    line_exist = tagLine(footprint, In_CHM, segment_info)

    flmc.log("Processing line {} done. Line exist: {}".format(fileSeg, line_exist))

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
        return failed_line

    return segment_info[0], line_exist, segment_info[2]

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
    global In_CHM
    In_CHM = args[1].rstrip()
    global Canopy_Raster
    Canopy_Raster = args[2].rstrip()
    global Cost_Raster
    Cost_Raster = args[3].rstrip()
    global In_Lidar_Year
    In_Lidar_Year = args[4].rstrip()
    global Maximum_distance_from_centerline
    Maximum_distance_from_centerline = float(args[5].rstrip()) / 2.0
    global Out_Tagged_Line
    Out_Tagged_Line = args[6].rstrip()
    outWorkspace = flmc.SetupWorkspace(workspaceName)

    # write params to text file
    f = open(outWorkspace + "\\params.txt", "w")
    f.write(outWorkspace + "\n")
    f.write(Centerline_Feature_Class + "\n")
    f.write(In_CHM + "\n")
    f.write(Canopy_Raster + "\n")
    f.write(Cost_Raster + "\n")
    f.write(In_Lidar_Year + "\n")
    f.write(str(Maximum_distance_from_centerline) + "\n")
    f.write(Out_Tagged_Line + "\n")
    f.close()

    # Remind if Status field is already in Shapefile
    if HasField(Centerline_Feature_Class, "Status"):
        print("{} has Status field, it will be overwritten.".format(Centerline_Feature_Class))

    polygons = retrievePolygons(In_Lidar_Year)

    # Prepare input lines for multiprocessing
    fields = flmc.GetAllFieldsFromShp(Centerline_Feature_Class)
    global ProcessSegments
    segment_all = flmc.SplitLines(Centerline_Feature_Class, outWorkspace,
                                  "LFP", ProcessSegments, fields, polygons)

    # TODO: inspect how GetCores works. Make sure it uses all the CPU cores
    pool = multiprocessing.Pool(processes=flmc.GetCores())
    flmc.log("Multiprocessing line corridors...")
    flmc.log("Using {} CPU cores".format(flmc.GetCores()))

    tagged_lines = pool.map(workLinesMem, segment_all)  # new version of memory based processing
    pool.close()
    pool.join()
    flmc.logStep("Tagging lines multiprocessing")

    flmc.log("Write lines with existence and all statistics...")
    try:
        # create tagged line feature class with stats
        (root, ext) = os.path.splitext(Out_Tagged_Line)
        root = root + "_stats"
        out_tagged_line_stats = root + ext
        arcpy.CreateFeatureclass_management(os.path.dirname(out_tagged_line_stats), os.path.basename(out_tagged_line_stats),
                                            "Polyline", "", "DISABLED", "DISABLED", Centerline_Feature_Class)
        arcpy.AddField_management(out_tagged_line_stats, "Status", "TEXT")

        arcpy.AddField_management(out_tagged_line_stats, "Mean", "DOUBLE")
        arcpy.AddField_management(out_tagged_line_stats, "Median", "DOUBLE")
        arcpy.AddField_management(out_tagged_line_stats, "Variance", "DOUBLE")
        arcpy.AddField_management(out_tagged_line_stats, "Stdev", "DOUBLE")

        arcpy.AddField_management(out_tagged_line_stats, "Mean_B", "DOUBLE")
        arcpy.AddField_management(out_tagged_line_stats, "Median_B", "DOUBLE")
        arcpy.AddField_management(out_tagged_line_stats, "Variance_B", "DOUBLE")
        arcpy.AddField_management(out_tagged_line_stats, "Stdev_B", "DOUBLE")

        fields_stats = ["SHAPE@", "Status", "Mean", "Median", "Variance", "Stdev",
                  "Mean_B", "Median_B", "Variance_B", "Stdev_B"]
        with arcpy.da.InsertCursor(out_tagged_line_stats, fields_stats) as cursor:
            for line in tagged_lines:
                cursor.insertRow([line[0]] + list(line[1]))

        # arcpy.Delete_management(fileMerge)
    except Exception as e:
        print(e)

    flmc.log("Writing lines with existence and all original attributes.")
    try:
        # create tagged line feature class with existence and all original attributes
        arcpy.CreateFeatureclass_management(os.path.dirname(Out_Tagged_Line), os.path.basename(Out_Tagged_Line),
                                            "Polyline", Centerline_Feature_Class,
                                            "DISABLED", "DISABLED", Centerline_Feature_Class)
        # Add Status field to indicate line existence type: confirmed, unconfirmed and invisible
        status_appended = False
        if not HasField(Centerline_Feature_Class, "Status"):
            arcpy.AddField_management(Out_Tagged_Line, "Status", "TEXT")
            fields.append("Status")
            status_appended = True

        with arcpy.da.InsertCursor(Out_Tagged_Line, ["Shape@"]+fields) as cursor:
            for line in tagged_lines:
                row = []
                for i in fields:
                    if i != "Status":
                        row.append(line[2][i])

                # Line status
                if status_appended:
                    row.append(line[1][0])
                else:  # overwrite Status value
                    row[fields.index("Status")] = line[1][0]

                cursor.insertRow([line[0]] + row)
    except Exception as e:
        print(e)

    flmc.logStep("Tagged lines output done.")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input("<Press any key to exit>")
