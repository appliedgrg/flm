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
# FLM_LineFootprint.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
# Refactor to use memory workspace to speedup processing
# Richard Zeng
# Date: 2021-August
# Refactor to use for produce dynamic footprint from dynamic canopy and cost raster
# Prerequisite:  Feature class must have the attribute Fields:"CorridorTh" "CanTh_HtM"
# FLM_DynamicLineFootprint.py
# Maverick Fong
# Date: 2021-Dec
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Creates dynamic footprint polygons for each input line based on a least
# cost corridor method and individual line thresholds.
#
# ---------------------------------------------------------------------------

# System imports
import os
import numpy
import multiprocessing

import math
from functools import partial

# ArcGIS imports
import sys

import arcpy
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_DLFPP_output"
outWorkspace = ""
Corridor_Threshold_Field = ""
Maximum_distance_from_centerline = 0


def Listline_forMatrix(cl_fc, process_segments, outWorkspace):
    outListline = []
    cl_Dict = {}
    if process_segments:
        arcpy.CreateFeatureclass_management(r"memory/", "splitedCL", "POLYLINE", cl_fc, None, None, cl_fc)
        arcpy.AddField_management(r"memory/splitedCL", "SLnID", "LONG")
        # create a list contains all the fields from simplified CL except geometry
        listfield = [field.name for field in arcpy.ListFields(r"memory/splitedCL") if field.type not in ['Geometry']]
        listfield.append("SHAPE@")

        outListline = flmc.SplitLines_Percentile(cl_fc, outWorkspace, process_segments)
        # arcpy.AddMessage(outListline)
        keys = outListline[0][2].keys()
        # arcpy.AddMessage(list(keys))
        out_list = []
        with arcpy.da.InsertCursor(r"memory/splitedCL", listfield) as iCursor:
            for record in outListline:
                in_record = []
                in_record.append(record[1])

                for col in listfield:
                    if col == 'SHAPE@':
                        in_record.append(record[0])
                    elif col in list(keys):
                        #        print(record[2].get(col))
                        if col != 'OBJECTID':
                            in_record.append(record[2].get(col))
                    elif col == "SLnID":
                        #       print(record[2].get('InLine_FID'))
                        # in_record.append(record[2].get('OBJECTID'))
                        if process_segments:
                            in_record.append(record[2].get('FID'))
                        else:
                            in_record.append(record[1])
                iCursor.insertRow(in_record)
                out_list.append(in_record)
        del iCursor
        outListline = []
        outListline = out_list

        cl_fc = os.path.normpath(r"memory/splitedCL")

    else:
        # make a copy the original feature class for the results
        arcpy.FeatureClassToFeatureClass_conversion(cl_fc, r"memory/", "splitedCL")

        # assign input centerlines feature class name and path for generate forest matrix results
        # cl_fc = os.path.join(os.path.dirname(cl_fc), os.path.basename(os.path.splitext(cl_fc)[0]) + "_CanThr.shp")
        cl_fc = os.path.normpath(r"memory/splitedCL")
        with arcpy.da.SearchCursor(cl_fc, ["OID@", "SHAPE@"]) as sCursor:
            for record in sCursor:
                outListline.append([record[0], record[1]])
        del sCursor

    return [outListline, cl_fc]


def CC_call(input_line):
    outWorkspace = r"memory"
    arcpy.env.workspace = r"memory"
    arcpy.env.scratchWorkspace = r"memory"
    arcpy.env.overwriteOutput = True

    try:
        # get params for Calculating Canopy and Cost Raster
        chm_raster = input_line[3]

        Min_Canopy_Height = float(input_line[2])

        # if Min_Canopy_Height < 0.5:
        #     Min_Canopy_Height = 0.5
        if Min_Canopy_Height < 0.0:
           Min_Canopy_Height = 0.05

        Tree_Search_Area = "Circle " + str(float(input_line[4])) + " MAP"
        Max_Line_Distance = float(input_line[5])
        CanopyAvoidance = float(input_line[6])
        Cost_Raster_Exponent = float(input_line[7])

        Output_Canopy_Raster = r"memory/out_canopy_raster" + str(input_line[0])

        tempbuffer = r"memory\outrbuffer" + str(input_line[0])

        # get params for footprint
        Centerline_Feature_Class = input_line[12]

        Corridor_Threshold_Field = input_line[8]

        Maximum_distance_from_centerline = input_line[9]
        Expand_And_Shrink_Cell_Range = input_line[10]

    except Exception as e:
        arcpy.AddMessage(
            "Something wrong getting parameter for line no.{}.......".format(str(input_line[0])))
        arcpy.AddMessage(e)

    try:
        # create a buffer for the input CL for clipping the CHM raster around the CL
        arcpy.Buffer_analysis(input_line[1], tempbuffer, "100 Meters", "FULL", "ROUND",
                              "NONE", None, "PLANAR")

        with arcpy.da.SearchCursor(tempbuffer, ["SHAPE@"]) as sCursor:
            for buffer in sCursor:
                desbuffer = buffer[0]
                SearchBox = str(desbuffer.extent.XMin) + " " + str(desbuffer.extent.YMin) + " " + str(
                    desbuffer.extent.XMax) + " " + str(desbuffer.extent.YMax)
        del sCursor
        #Clip the CHM with buffer area for Canopy and cost raster creation
        CHMClipM = r"memory\clipCHM_" + str(input_line[0])
        with arcpy.EnvManager(snapRaster=chm_raster):  # clip the raster using the buffered area

            arcpy.Clip_management(chm_raster, SearchBox, CHMClipM, tempbuffer, "-99999",
                                  "ClippingGeometry", "NO_MAINTAIN_EXTENT")

    except Exception as e:
        arcpy.AddMessage(
            "Something wrong Create buffer for line no.{}.......".format(str(input_line[0])))
        arcpy.AddMessage(e)

    chm_raster = arcpy.Raster(CHMClipM)
    # Local variables:

    FLM_CC_EucRaster = outWorkspace + "\\FLM_CC_EucRaster" + str(input_line[0])
    FLM_CC_SmoothRaster = outWorkspace + "\\FLM_CC_SmoothRaster" + str(input_line[0])
    FLM_CC_Mean = outWorkspace + "\\FLM_CC_Mean" + str(input_line[0])
    FLM_CC_StDev = outWorkspace + "\\FLM_CC_StDev" + str(input_line[0])
    FLM_CC_CostRaster = outWorkspace + "\\FLM_CC_CostRaster" + str(input_line[0])

    # Process: Turn CHM into a Canopy Closure (CC) map
    arcpy.gp.Con_sa(chm_raster, 1, Output_Canopy_Raster, 0, "VALUE > " + str(Min_Canopy_Height))

    # Process: CC Mean
    # arcpy.AddMessage("Calculating Focal Mean...")
    arcpy.gp.FocalStatistics_sa(Output_Canopy_Raster, FLM_CC_Mean, Tree_Search_Area, "MEAN")

    # Process: CC StDev
    # arcpy.AddMessage("Calculating Focal StDev..")
    arcpy.gp.FocalStatistics_sa(Output_Canopy_Raster, FLM_CC_StDev, Tree_Search_Area, "STD")

    # Process: Euclidean Distance
    # arcpy.AddMessage("Calculating Euclidean Distance From Canopy...")
    EucAllocation(Con(arcpy.Raster(Output_Canopy_Raster) >= 1, 1, ""), "", "", "", "", FLM_CC_EucRaster, "")

    smoothCost = (float(Max_Line_Distance) - arcpy.Raster(FLM_CC_EucRaster))
    smoothCost = Con(smoothCost > 0, smoothCost, 0) / float(Max_Line_Distance)
    smoothCost.save(FLM_CC_SmoothRaster)

    # Process: Cost Raster Calculation
    # arcpy.AddMessage("Calculating Cost Raster for FID:{}......".format(input_line[1]))
    arcpy.env.compression = "NONE"
    Raster_CC = arcpy.Raster(Output_Canopy_Raster)
    Raster_Mean = arcpy.Raster(FLM_CC_Mean)
    Raster_StDev = arcpy.Raster(FLM_CC_StDev)
    Raster_Smooth = arcpy.Raster(FLM_CC_SmoothRaster)
    avoidance = max(min(float(CanopyAvoidance), 1), 0)

    # Original formula as follow
    # outRas = Power(Exp(Con((Raster_CC == 1), 1, Con((Raster_Mean + Raster_StDev <= 0), 0, (
    # 			1 + (Raster_Mean - Raster_StDev) / (Raster_Mean + Raster_StDev)) / 2) * (
    # 								   1 - avoidance) + Raster_Smooth * avoidance)), float(Cost_Raster_Exponent))

    #decomposite above formula to steps
    with arcpy.EnvManager(snapRaster=chm_raster):

        aM = (1 + (Raster_Mean - Raster_StDev) / (Raster_Mean + Raster_StDev)) / 2
        aaM = (Raster_Mean + Raster_StDev)
        bM = arcpy.sa.Con(aaM, 0, aM, "Value <= 0")
        cM = bM * (1 - avoidance) + (Raster_Smooth * avoidance)
        dM = arcpy.sa.Con(Raster_CC, 1, cM, "Value = 1")
        eM = arcpy.sa.Exp(dM)
        outRas = arcpy.sa.Power(eM, float(Cost_Raster_Exponent))


    Canopy_Raster = Raster_CC
    Cost_Raster = outRas
    del aM, aaM, bM, cM, dM, eM

    # TODO: this is constant, but need to be investigated.
    ################################# Input Test Corridor Threshold here #############################################
    Corridor_Threshold = 3

    ##Or

    # if Min_Canopy_Height>Corridor_Threshold_Field:
    #     Corridor_Threshold = Min_Canopy_Height
    # else:
    #     Corridor_Threshold= Corridor_Threshold_Field

    ##################################################################################################################
    lineNo = input_line[0]  # first element is the line No.
    outWorkspaceMem = r"memory"

    # Temporary files
    fileSeg = os.path.join(outWorkspaceMem, "FLM_LFP_Segment_" + str(lineNo))
    fileOrigin = os.path.join(outWorkspaceMem, "FLM_LFP_Origin_" + str(lineNo))
    fileDestination = os.path.join(outWorkspaceMem, "FLM_LFP_Destination_" + str(lineNo))
    fileBuffer = os.path.join(outWorkspaceMem, "FLM_LFP_Buffer_" + str(lineNo))

    fileClip = os.path.join(outWorkspaceMem, "FLM_LFP_Clip_" + str(lineNo))
    fileCostDa = os.path.join(outWorkspaceMem, "FLM_LFP_CostDa_" + str(lineNo))
    fileCostDb = os.path.join(outWorkspaceMem, "FLM_LFP_CostDb_" + str(lineNo))
    fileCorridor = os.path.join(outWorkspaceMem, "FLM_LFP_Corridor_" + str(lineNo))
    fileCorridorMin = os.path.join(outWorkspaceMem, "FLM_LFP_CorridorMin_" + str(lineNo))
    fileThreshold = os.path.join(outWorkspaceMem, "FLM_LFP_Threshold_" + str(lineNo))
    fileExpand = os.path.join(outWorkspaceMem, "FLM_LFP_Expand_" + str(lineNo))
    fileShrink = os.path.join(outWorkspaceMem, "FLM_LFP_Shrink_" + str(lineNo))
    fileClean = os.path.join(outWorkspaceMem, "FLM_LFP_Clean_" + str(lineNo))
    fileNull = os.path.join(outWorkspaceMem, "FLM_LFP_Null_" + str(lineNo))# + ".tif")

    # Load segment list
    segment_list = []

    for line in input_line[1]:
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
        cursor.insertRow([input_line[1]])
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
        RasterClass = SetNull(IsNull(Raster(fileCorridorMin)),
                              (Raster(fileCorridorMin) + (Raster(Canopy_Raster) >= 1)) > 0)
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
                                                     "SIMPLIFY", "VALUE", "MULTIPLE_OUTER_PART", "")
    except Exception as e:
        print(e)

    #flmc.log("Processing line {} done".format(fileSeg))
    print("Processing line {} done".format(fileSeg))

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

    arcpy.ClearWorkspaceCache_management()
    arcpy.Delete_management(r"memory/")
    del Raster_CC
    del Raster_Mean
    del Raster_StDev
    del Raster_Smooth
    del avoidance
    del smoothCost
    del outRas

    return footprint  # list of polygons


def main(argv=None):
    # Setup script path and workspace folder
    workspaceName = "FLM_DLFPP_output"
    global outWorkspace
    outWorkspace = flmc.SetupWorkspace_2(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_DLFPP_params.txt")

    # Tool arguments
    global Centerline_Feature_Class
    Centerline_Feature_Class = args[0].rstrip()
    global CHM_Raster
    CHM_Raster = args[1].rstrip()
    global Maximum_distance_from_centerline
    Maximum_distance_from_centerline = float(args[2].rstrip()) / 2.0
    global Expand_And_Shrink_Cell_Range
    Expand_And_Shrink_Cell_Range = args[3].rstrip()
    global ProcessSegments
    ProcessSegments = args[4].rstrip()
    if ProcessSegments == "False":
        ProcessSegments = False
    else:
        ProcessSegments = True
    global Output_Footprint
    Output_Footprint = args[5].rstrip()

    global TreeSearchRadius
    TreeSearchRadius = float(args[6].rstrip())
    global MaximumLineDistance
    MaximumLineDistance = float(args[7].rstrip())
    global CanopyAvoidance
    CanopyAvoidance = float(args[8].rstrip())
    global CostRasterExponent
    CostRasterExponent = float(args[9].rstrip())

    global Corridor_Threshold_Field
    global Canopy_Threshold_Field

    f = open(outWorkspace + "\\params.txt", "w")
    f.write(Centerline_Feature_Class + "\n")
    f.write(CHM_Raster + "\n")
    f.write(str(Maximum_distance_from_centerline) + "\n")
    f.write(Expand_And_Shrink_Cell_Range + "\n")
    f.write(str(ProcessSegments) + "\n")
    f.write(Output_Footprint + "\n")
    f.write(str(TreeSearchRadius) + "\n")
    f.write(str(MaximumLineDistance) + "\n")
    f.write(str(CanopyAvoidance) + "\n")
    f.write(str(CostRasterExponent))
    f.close()

    arcpy.env.overwriteOutput = True
    try:
        arcpy.CheckOutExtension("3D")
        
        arcpy.CheckOutExtension("Spatial")

    except Exception as e:
        print("e") 
       
    input_CL_fc=r"memory/Centerline_Feature_Class"
    check_field=["CorridorTh", "CanTh_HtM"]
    found=0
    for field in check_field:
        if field in [fields.name for fields in arcpy.ListFields(Centerline_Feature_Class)]:
            if field == "CorridorTh":
                Corridor_Threshold_Field = "CorridorTh"
                found=found+1
            elif field == "CanTh_HtM":
                Canopy_Threshold_Field = "CanTh_HtM"
                found = found + 2

    if found==1:
        flmc.log("Error: Dynamic Canopy Threshold field is NOT found.  Please create Dynamic Canopy Threshold before run this step")
        print("Tool stops")
        sys.exit()
    elif found==2:
        flmc.log("Dynamic Canopy Threshold field is found. but NO Corridor Threshold Field is found.  Default value will be applied.")
        arcpy.AddField_management(Centerline_Feature_Class, "CorridorTh", "DOUBLE")
        arcpy.CalculateField_management(Centerline_Feature_Class, "CorridorTh", "3") ## To be investigate

        Corridor_Threshold_Field = "CorridorTh"

    elif found == 3:
        flmc.log("Dynamic Canopy Threshold and Corridor Thershold field are found.")
        print(Corridor_Threshold_Field)
        print(Canopy_Threshold_Field)


    print("Line Setup........")
    CL_fc_Alllistline = Listline_forMatrix(Centerline_Feature_Class, ProcessSegments, outWorkspace)
    input_CL_fc = CL_fc_Alllistline[1]

    segment_all_Cal_DynCC=[]
    print("Preparing lines for Dynamic Footprint........")
    with arcpy.da.SearchCursor(input_CL_fc,["OID@","SHAPE@","CanTh_HtM"]) as sCursor:
        for item in sCursor:
            seg = []
            seg.append(item[0])
            seg.append(item[1])
            seg.append(item[2])
            seg.append(CHM_Raster)
            seg.append(TreeSearchRadius)
            seg.append(MaximumLineDistance)
            seg.append(CanopyAvoidance)
            seg.append(CostRasterExponent)
            seg.append(Corridor_Threshold_Field)
            seg.append(Maximum_distance_from_centerline)
            seg.append(Expand_And_Shrink_Cell_Range)
            seg.append(Canopy_Threshold_Field)
            seg.append(Centerline_Feature_Class)
            segment_all_Cal_DynCC.append(seg)
    print("Start generate Dynamic Footprint........")

    pool = multiprocessing.Pool(processes=flmc.GetCores())

    flmc.log("Multiprocessing for dynamic canopy cost raster...")
    flmc.log("Using {} CPU cores".format(flmc.GetCores()))

    footprints = pool.map(CC_call, segment_all_Cal_DynCC)

    pool.close()
    pool.join()

    flmc.log("Merging footprints...")

    try:
        # Flatten footprints which is a list of list
        ft_list = [item for sublist in footprints for item in sublist]

        fileMerge = outWorkspace + "\\FLM_LFP_Merge.shp"
        arcpy.Merge_management(ft_list, fileMerge)
        arcpy.Dissolve_management(fileMerge, Output_Footprint)
        arcpy.Delete_management(fileMerge)
    except Exception as e:
        print("e")

    flmc.logStep("Footprints merged.")
    arcpy.CheckInExtension("Spatial")
    arcpy.CheckInExtension("3D")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input("<Press any key to exit>")
