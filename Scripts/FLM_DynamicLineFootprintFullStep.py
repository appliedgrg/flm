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
# FLM_DynamicLineFootprintFullStep.py
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
import sys
import numpy
import multiprocessing

import math
from functools import partial
from memory_profiler import profile

# ArcGIS imports
import arcpy
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_DLFP_output"
outWorkspace = ""
Corridor_Threshold_Field = ""
Maximum_distance_from_centerline = 0

def PathFile(path):
    return path[path.rfind("\\") + 1:]


def CopyParallel(plyP, sLength):

    part = plyP.getPart(0)
    lArray = arcpy.Array()
    rArray = arcpy.Array()
    for ptX in part:
        dL = plyP.measureOnLine(ptX)
        ptX0 = plyP.positionAlongLine(dL - 0.01).firstPoint
        ptX1 = plyP.positionAlongLine(dL + 0.01).firstPoint
        dX = float(ptX1.X) - float(ptX0.X)
        dY = float(ptX1.Y) - float(ptX0.Y)
        lenV = math.hypot(dX, dY)
        sX = -dY * sLength / lenV
        sY = dX * sLength / lenV
        leftP = arcpy.Point(ptX.X + sX, ptX.Y + sY)
        lArray.add(leftP)
        rightP = arcpy.Point(ptX.X - sX, ptX.Y - sY)
        rArray.add(rightP)

    leftsection = arcpy.Polyline(lArray)
    rightsection = arcpy.Polyline(rArray)

    return leftsection, rightsection


def addFields(Splited_cl, Canopy_Percentile_Field,CanopyTh_Field):
    try:  # rest and recreate Canopy Percentile in simplified Left centerline table
        if arcpy.ListFields(Splited_cl, Canopy_Percentile_Field + "L"):
            arcpy.DeleteField_management(Splited_cl, Canopy_Percentile_Field + "L")
            arcpy.AddField_management(Splited_cl, Canopy_Percentile_Field + "L", "Double")
        else:
            arcpy.AddField_management(Splited_cl, Canopy_Percentile_Field + "L", "Double")
    except Exception as e:
        arcpy.AddMessage("Error Adding Canopy Percentile Field: {}".format(e))
        del e
        sys.exit()
    try:  # rest and recreate Canopy Percentile in simplified Right centerline table
        if arcpy.ListFields(Splited_cl, Canopy_Percentile_Field + "R"):
            arcpy.DeleteField_management(Splited_cl, Canopy_Percentile_Field + "R")
            arcpy.AddField_management(Splited_cl, Canopy_Percentile_Field + "R", "Double")
        else:
            arcpy.AddField_management(Splited_cl, Canopy_Percentile_Field + "R", "Double")
    except Exception as e:
        arcpy.AddMessage("Error Adding Canopy Percentile Field: {}".format(e))
        del e
        sys.exit()

    try:  # rest and recreate Canopy Threshold height simplified Left in centerline table
        if arcpy.ListFields(Splited_cl, CanopyTh_Field + "L"):
            arcpy.DeleteField_management(Splited_cl, CanopyTh_Field + "L")
            arcpy.AddField_management(Splited_cl, CanopyTh_Field + "L", "Double")
        else:
            arcpy.AddField_management(Splited_cl, CanopyTh_Field + "L", "Double")
    except Exception as e:
        arcpy.AddMessage("Error Adding Canopy Percentile Field: {}".format(e))
        del e
        sys.exit()

    try:  # rest and recreate Canopy Threshold height simplified Right in centerline table
        if arcpy.ListFields(Splited_cl, CanopyTh_Field + "R"):
            arcpy.DeleteField_management(Splited_cl, CanopyTh_Field + "R")
            arcpy.AddField_management(Splited_cl, CanopyTh_Field + "R", "Double")
        else:
            arcpy.AddField_management(Splited_cl, CanopyTh_Field + "R", "Double")
    except Exception as e:
        arcpy.AddMessage("Error Adding Canopy Threshold Field: {}".format(e))
        del e
        sys.exit()

    try:  # rest and recreate Mean Canopy Threshold height in centerline table
        if arcpy.ListFields(Splited_cl, CanopyTh_Field + "M"):
            arcpy.DeleteField_management(Splited_cl, CanopyTh_Field + "M")
            arcpy.AddField_management(Splited_cl, CanopyTh_Field + "M", "Double")
        else:
            arcpy.AddField_management(Splited_cl, CanopyTh_Field + "M", "Double")
    except Exception as e:
        arcpy.AddMessage("Error Adding Canopy Threshold Field: {}".format(e))
        del e

    if arcpy.ListFields(Splited_cl, "Search_R"):
        arcpy.DeleteField_management(Splited_cl, "Search_R")
        arcpy.AddField_management(Splited_cl, "Search_R", "DOUBLE")
    else:
        arcpy.AddField_management(Splited_cl, "Search_R", "DOUBLE")

    if arcpy.ListFields(Splited_cl, "Buf_Side"):
        arcpy.DeleteField_management(Splited_cl, "Buf_Side")
        arcpy.AddField_management(Splited_cl, "Buf_Side", "TEXT")
    else:
        arcpy.AddField_management(Splited_cl, "Buf_Side", "TEXT")

    if arcpy.ListFields(Splited_cl, "CorridorTh"):
        pass
    else:
        arcpy.AddField_management(Splited_cl, "CorridorTh", "DOUBLE")

    arcpy.CalculateField_management(Splited_cl, "Search_R", Search_R)

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

def Forest_Matrix_Percentile_S(seg_all, chm, Canopy_Percentile, CanopyTh_Percent,
                               pointsAlongParallelLine, ProcessSegments,Canopy_Percentile_FieldL, Canopy_Percentile_FieldR
                                    , CanopyTh_FieldL, CanopyTh_FieldR, Buf_Side, CanopyTh_FieldM, CorridorTh,split_simCL):
    arcpy.env.overwriteOutput = True
    #print("Start doing simple CL: {}".format(seg_all[0]))
    chm = arcpy.Raster(chm)
    arcpy.env.snapRaster = (chm)
    Canopy_Percentile_value = int(Canopy_Percentile)

    # Check the canopy threshold percent in 0-100 range.  If it is not, 50% will be applied
    if 100.0 > float(int(CanopyTh_Percent)) > 0.0:
        CanopyTh_Percent_value = float(int(CanopyTh_Percent) / 100)
    else:
        # set the Canopy Threshold percentage to 50% (0.5)
        CanopyTh_Percent_value = 0.5

    # Set Current record ID = Feature ID# from the input List
    print("Calculate {}th Percentile for simplified CL FID:{}.".format(str(Canopy_Percentile), seg_all[0]))
    currentRecord = str(seg_all[0])

    # Set the SQL Select statement for returning features with Original FID and buffer side 'Left' or 'Right'
    if ProcessSegments:
        OFID = "SLnID"
        whereclausel = OFID + " = " + str(seg_all[0]) + " And Buf_Side = 'LEFT'"

        whereclauser = OFID + " = " + str(seg_all[0]) + " And Buf_Side = 'RIGHT'"

        record_ID = seg_all[0]

    else:
        OFID = "InLine_FID"
        whereclausel = OFID + " = " + str(seg_all[0] - 1) + " And Buf_Side = 'LEFT'"

        whereclauser = OFID + " = " + str(seg_all[0] - 1) + " And Buf_Side = 'RIGHT'"

        record_ID = seg_all[0]

    try:
        # SQL selection is result in two subsets of input point feature class (parallel points on 'Left' and 'Right' \
        # with current record ID
        arcpy.MakeFeatureLayer_management(pointsAlongParallelLine, "Point_CanThr_Left" + currentRecord, whereclausel)

        nl_fcL = "Point_CanThr_Left" + currentRecord
        arcpy.MakeFeatureLayer_management(pointsAlongParallelLine, "Point_CanThr_Right" + currentRecord, whereclauser)

        nl_fcR = "Point_CanThr_Right" + currentRecord


    except Exception as e:
        print("Selecting Surrounding points of line feature ID: {} failed.".format(str(seg_all[0])))
        print(e)

    try:

        with arcpy.da.SearchCursor(nl_fcL, [OFID, "Z", "SHAPE@"]) as uCursor1L:
            CHM_listL = []

            for rowL in uCursor1L:
                if rowL[2]:
                    CHM_listL.append(rowL[1])

            CHM_listL.sort
            del uCursor1L
        with arcpy.da.SearchCursor(nl_fcR, [OFID, "Z", "SHAPE@"]) as uCursor1R:
            CHM_listR = []

            for rowR in uCursor1R:
                if rowR[2]:
                    CHM_listR.append(rowR[1])

            CHM_listR.sort
            del uCursor1R
    except Exception as e:
            print(e)
            print("somthing wrong when sort the Nth Precentile list")
    try:
        resultlist = []
        resultlist.append(record_ID)
        result_PercentileL = numpy.percentile(CHM_listL, Canopy_Percentile_value)
        resultlist.append(result_PercentileL)
        result_PercentileR = numpy.percentile(CHM_listR, Canopy_Percentile_value)
        resultlist.append(result_PercentileR)
        CanopyThL = result_PercentileL * CanopyTh_Percent_value
        resultlist.append(CanopyThL)
        CanopyThR = result_PercentileR * CanopyTh_Percent_value
        resultlist.append(CanopyThR)
        return resultlist
    except Exception as e:
        arcpy.AddMessage("Something wrong when calculating Percentile for line {}".format(str(record_ID)))
        resultlist = []
        resultlist.append(record_ID)
        result_PercentileL = 0
        resultlist.append(result_PercentileL)
        result_PercentileR = 0
        resultlist.append(result_PercentileR)
        CanopyThL = 0
        resultlist.append(CanopyThL)
        CanopyThR = 0
        resultlist.append(CanopyThR)
        return resultlist
        arcpy.AddMessage(e)

# TODO: 'update_simpCL' Can be deleted
def update_simpCL(seg,fieldName,split_simCL, wherecluase):
    #mutliprocess updating for simplified CL
    #problem occurs when multi-access 'split_simCL' dataset, error: Cannot acquire lock
    print("Updating Line:{}.".format(seg[0]-1))
    # print(fieldName)


    try:
        sqlcluase = "{}={}".format(wherecluase,seg[0] - 1)
    # print(wherecluase)
    except Exception as e:
        print("Cannot create wherecluase")
        print(e)
    # try:
    #     selected_lyr=arcpy.SelectLayerByAttribute_management(split_simCL,"NEW_SELECTION",sqlcluase)
    #
    # except Exception as e:
    #     print("Cannot create Selected SimCL layer")
    #     print(e)

    try:
        upcursor = arcpy.da.UpdateCursor(split_simCL,fieldName,sqlcluase)
    except Exception as e:
        print(e)
        print("Cannot create UpdateCursor for simple CL {}".format(seg[0]))
    # arcpy.SelectLayerByAttribute_management(split_simCL, "CLEAR_SELECTION", sqlcluase)
    try:
        for row in upcursor:

            row[1] = seg[1]
            row[2] = seg[2]
            row[3] = seg[3]
            row[4] = seg[4]
            if seg[1] != 0 and seg[3] != 0:
                row[5] = "Left, Right"
            elif seg[2] == None and seg[4] != 0:
                row[5] = "Right"
            elif seg[2] != 0 and seg[4] == None:
                row[5] = "Left"
            else:
                row[5] = "None"

            row[6] = (seg[3] + seg[4]) / 2

            upcursor.updateRow(row)

        del upcursor

    except Exception as e:
        print(e)

        print("Cannot Update simpCL for simple CL {}".format(seg[0]))

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
        return

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

        # Clip the CHM with buffer area for Canopy and cost raster creation
        CHMClipM = r"memory\clipCHM_" + str(input_line[0])
        with arcpy.EnvManager(snapRaster=chm_raster):  # clip the raster using the buffered area
            arcpy.Clip_management(chm_raster, SearchBox, CHMClipM, tempbuffer, "-99999",
                                  "ClippingGeometry", "NO_MAINTAIN_EXTENT")
    except Exception as e:
        arcpy.AddMessage(
            "Something wrong Create buffer for line no.{}.......".format(str(input_line[0])))
        arcpy.AddMessage(e)
        return

    chm_raster = arcpy.Raster(CHMClipM)

    # Local variables:
    FLM_CC_EucRaster = outWorkspace + "\\FLM_CC_EucRaster" + str(input_line[0])
    FLM_CC_SmoothRaster = outWorkspace + "\\FLM_CC_SmoothRaster" + str(input_line[0])
    FLM_CC_Mean = outWorkspace + "\\FLM_CC_Mean" + str(input_line[0])
    FLM_CC_StDev = outWorkspace + "\\FLM_CC_StDev" + str(input_line[0])
    FLM_CC_CostRaster = outWorkspace + "\\FLM_CC_CostRaster" + str(input_line[0])

    try:
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
    except Exception as e:
        print(e)
        print(input_line)
        return

    try:
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

        # decomposite above formula to steps
        with arcpy.EnvManager(snapRaster=chm_raster):

            aM = (1 + (Raster_Mean - Raster_StDev) / (Raster_Mean + Raster_StDev)) / 2
            aaM = (Raster_Mean + Raster_StDev)
            bM = arcpy.sa.Con(aaM, 0, aM, "Value <= 0")
            cM = bM * (1 - avoidance) + (Raster_Smooth * avoidance)
            dM = arcpy.sa.Con(Raster_CC, 1, cM, "Value = 1")
            eM = arcpy.sa.Exp(dM)
            outRas = arcpy.sa.Power(eM, float(Cost_Raster_Exponent))
    except Exception as e:
        print(e)
        print(input_line)
        return

    Canopy_Raster = Raster_CC
    Cost_Raster = outRas
    del aM, aaM, bM, cM, dM, eM

    # TODO: this is constant, but need to be investigated.
    ################################# Input Test Corridor Threshold here #############################################
    Corridor_Threshold = 3

    ## Or

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
        return

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
        return

    # flmc.log("Processing line {} done".format(fileSeg))
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

        arcpy.Delete_management(Output_Canopy_Raster)
        arcpy.Delete_management(tempbuffer)
        arcpy.Delete_management(CHMClipM)
        arcpy.Delete_management(Raster_CC)
        arcpy.Delete_management(Raster_StDev)
        arcpy.Delete_management(Raster_Smooth)
        arcpy.Delete_management(smoothCost)

        arcpy.Delete_management(FLM_CC_EucRaster)
        arcpy.Delete_management(FLM_CC_SmoothRaster)
        arcpy.Delete_management(FLM_CC_Mean)
        arcpy.Delete_management(FLM_CC_StDev)
    except Exception as e:
        print("Line Footprint: Deleting temporary file failed. Inspect later.")
        return

    # arcpy.ClearWorkspaceCache_management()
    # arcpy.Delete_management(r"memory/")
    del Raster_CC
    del Raster_StDev
    del Raster_Smooth
    del avoidance
    del smoothCost
    del outRas

    return footprint  # list of polygons

# decorated_worker = profile(_CC_call)
# def CC_call(*args, **kwargs):
#     return decorated_worker(*args, **kwargs)
def Percentile_Call(workspaceName, outWorkspace, Centerline_Feature_Class, Output_Footprint, chm, Search_R,
                    Canopy_Percentile, CanopyTh_Percent, ProcessSegments,
                    TreeSearchRadius, MaximumLineDistance, CanopyAvoidance, CostRasterExponent):
    # outWorkspace = flmc.SetupWorkspace(workspaceName)
    # outWorkspace = flmc.GetWorkspace(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True
    cl_fc = Centerline_Feature_Class


    Canopy_Percentile_value = int(Canopy_Percentile)
    Canopy_Percentile_Field = "P" + str(Canopy_Percentile_value) + "_R" + str(Search_R)
    CanopyTh_Field = "CanTh_Ht"  # assign new field name for computed Canopy Threshold height

    run_in_mem = True
    outrbuffer = r"memory/rbuffer_"
    outWspace = r"memory/"

    print("Run in memory")
    arcpy.CheckOutExtension("Spatial")

    if ProcessSegments:
        ProcMode="_AllSegPro"
    else:
        ProcMode = "_WholeLinePro"


    # create a simplify centerlines from input centerlines for parallel copy
    print("Simplify input centerline......")
    simplify_cl = r"memory/simplify_CL"
    with arcpy.EnvManager(transferGDBAttributeProperties="NOT_TRANSFER_GDB_ATTRIBUTE_PROPERTIES"):
        arcpy.SimplifyLine_cartography(cl_fc, simplify_cl,
                                       "BEND_SIMPLIFY", "5 Meters", "RESOLVE_ERRORS", None, "CHECK", None)


    # Prepare list of all input centerline for multiprocessing
    print("Lines Setup for input centerline.....")

    CL_fc_Alllistline = Listline_forMatrix(cl_fc, ProcessSegments, outWorkspace)
    Splited_cl=CL_fc_Alllistline[1]
    #addFields(Splited_cl, Canopy_Percentile_Field, CanopyTh_Field)
    Cl_Alllistline = (CL_fc_Alllistline[0])
    #arcpy.management.CalculateField(Splited_cl, "SLnID", "!OBJECTID!")

    Percentile_CL= os.path.abspath(os.path.dirname(Output_Footprint) + "/" \
                                 + os.path.basename(Centerline_Feature_Class).rpartition('.')[
                                     0] + ProcMode+"_Percentile_CL.shp")

    before_updated_Percentile_CL = r"memory/before_Percentile_CL"
    #arcpy.CopyFeatures_management(Splited_cl, Percentile_CL)
    arcpy.CopyFeatures_management(Splited_cl, before_updated_Percentile_CL)


    # Prepare list of all input simplified centerline for multiprocessing
    print("Lines Setup for input simplified centerline")
    simplify_Alllistline = Listline_forMatrix(simplify_cl, ProcessSegments, outWorkspace)
    Splited_simplify_cl = os.path.normpath(simplify_Alllistline[1])
    Alllistline = (simplify_Alllistline[0])

    # Add Field "Search_R" to CL feature
    # addFields_forsimplified_line(Splited_simplify_cl, int(Search_R))
    addFields(Splited_simplify_cl, Canopy_Percentile_Field, CanopyTh_Field)
    arcpy.management.CalculateField(Splited_simplify_cl, "SLnID", "!OBJECTID!")


    workspace = os.path.dirname(Splited_simplify_cl)
    # create a copy parallel polyline class
    # create a list contains all the fields from simplified CL except geometry
    lstFields = [field.name for field in arcpy.ListFields(Splited_simplify_cl) if field.type not in ['Geometry']]
    # Append Geometry at the end of the list
    lstFields.append("SHAPE@")
    # Get the list index for field: "CorridorTh"
    CorridorTh_index = (lstFields.index("CorridorTh"))
    # Get the list index for field: "Buf_Side"
    Buf_Side_index = (lstFields.index("Buf_Side"))
    # Get the list index for field: "Search_R"
    Search_R_index = (lstFields.index("Search_R"))
    # Get the list index for field: "Shape@" geometry
    lastitem_index = len(lstFields) - 1

    # Copy a new simplified lines FC for parallel lines (left and right)
    Splited_simplify_parallelline = r"memory/simplify_parallelline"
    arcpy.CopyFeatures_management(Splited_simplify_cl, Splited_simplify_parallelline)
    Temp_Splited_simplify_cl=os.path.abspath(os.path.dirname(Output_Footprint) + "/" \
                                 + os.path.basename(Centerline_Feature_Class).rpartition('.')[
                                     0] + ProcMode+"_Simplified_CL.shp")
    arcpy.CopyFeatures_management(Splited_simplify_cl,Temp_Splited_simplify_cl)


    arcpy.AddMessage("Copy parallel lines from simplified centerline......")
    edit = arcpy.da.Editor(workspace)
    edit.startEditing(False, True)
    edit.startOperation()
    inCursor = arcpy.da.InsertCursor(Splited_simplify_parallelline, lstFields)
    with arcpy.da.UpdateCursor(Splited_simplify_parallelline, lstFields) as cursor:
        for row in cursor:
            if row[lastitem_index]:
                twoLines = CopyParallel(row[lastitem_index], row[Search_R_index])
                row[Buf_Side_index] = "LEFT"
                row[-1] = twoLines[0]
                cursor.updateRow(row)
                row[Buf_Side_index] = "RIGHT"
                row[-1] = twoLines[1]
                inCursor.insertRow(row)
    del cursor
    del inCursor
    del Buf_Side_index
    del Search_R_index
    del lastitem_index
    del lstFields
    # del twoLines

    edit.stopOperation()
    edit.stopEditing(True)


    # Get raster cell size equivalent for points interval
    CHMCellx = arcpy.GetRasterProperties_management(chm, "CELLSIZEX").getOutput(0)

    CHMCelly = arcpy.GetRasterProperties_management(chm, "CELLSIZEY").getOutput(0)

    Cell_size = 100 * (float(CHMCellx) + float(CHMCelly)) / 2
    points_interval = str(Cell_size) + " Meters"
    # arcpy.AddMessage(points_interval)

    # Generate points along simplified parallel lines (left and right) @ Cell Size interval
    arcpy.AddMessage(
        "Generate raster cell size equivalent ({}) interval points along parallel lines......".format(points_interval))
    with arcpy.EnvManager(outputZFlag="Enabled", outputMFlag="Enabled"):
        arcpy.management.GeneratePointsAlongLines(Splited_simplify_parallelline, r"memory/pointalonglines",
                                                  "DISTANCE", points_interval, None, "END_POINTS")
    arcpy.AddMessage(
        "Generate raster cell size equivalent ({}) interval points along parallel lines......Done".format(
            points_interval))

    # assign output points feature class name and path from the results of parallel lines
    mem_pointsAlongParallelLine = r"in_memory/pointsAlongParallelLine"

    # Add Z value base on CHM into points along parallel line
    arcpy.AddMessage("Interpolate points Z value")
    arcpy.ddd.InterpolateShape(chm, r"memory/pointalonglines", mem_pointsAlongParallelLine, None, 1, "NEAREST",
                               "VERTICES_ONLY",
                               0, "EXCLUDE")
    arcpy.Delete_management(r"memory/pointalonglines")


    if arcpy.ListFields(mem_pointsAlongParallelLine, "Z"):
        arcpy.DeleteField_management(mem_pointsAlongParallelLine, "Z")
        arcpy.AddField_management(mem_pointsAlongParallelLine, "Z", "DOUBLE")
    else:
        arcpy.AddField_management(mem_pointsAlongParallelLine, "Z", "DOUBLE")

    arcpy.management.CalculateGeometryAttributes(mem_pointsAlongParallelLine, "Z POINT_Z", '', '', None, "SAME_AS_INPUT")


    pointsAlongParallelLine = os.path.dirname(Output_Footprint) + "/" \
                             + os.path.basename(Centerline_Feature_Class).rpartition('.')[0]  + ProcMode+ "_ParallelPts.shp"
    arcpy.CopyFeatures_management(mem_pointsAlongParallelLine, pointsAlongParallelLine)

    #arcpy.Delete_management("PointsAlongParalelineLy")
    arcpy.Delete_management(mem_pointsAlongParallelLine)

    # multiprocessing for Canopy Percentile and Canopy Threshold (lef and right)
    arcpy.AddMessage("Create Canopy Percentile and Threshold......")

    seg_line1 = partial(Forest_Matrix_Percentile_S, chm=chm, Canopy_Percentile=Canopy_Percentile,
                       CanopyTh_Percent=CanopyTh_Percent,
                       pointsAlongParallelLine=pointsAlongParallelLine, ProcessSegments=ProcessSegments,
                       Canopy_Percentile_FieldL=Canopy_Percentile_Field + "L", Canopy_Percentile_FieldR=Canopy_Percentile_Field + "R"
                       , CanopyTh_FieldL=CanopyTh_Field + "L", CanopyTh_FieldR=CanopyTh_Field + "R", Buf_Side="Buf_Side",
                       CanopyTh_FieldM=CanopyTh_Field + "M", CorridorTh="CorridorTh", split_simCL=Temp_Splited_simplify_cl)



    arcpy.AddMessage("Multiprocessing Canopy Threshold calculation...")
    arcpy.AddMessage("Using {} CPU cores".format(str(multiprocessing.cpu_count())))
    wherecluase = arcpy.Describe(Temp_Splited_simplify_cl).OIDFieldName

    fieldNames = ["OID@", Canopy_Percentile_Field + "L", Canopy_Percentile_Field + "R", CanopyTh_Field + "L",
                  CanopyTh_Field + "R", "Buf_Side", CanopyTh_Field + "M", "CorridorTh", "SHAPE@"]
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())

    with arcpy.da.Editor(os.path.dirname(pointsAlongParallelLine)) as edit:

        updated_simCL_list=pool.map(seg_line1, Alllistline)

        print("Updating Percentile Statistic into CL attributes........")

        for seg in updated_simCL_list:
            try:
                sqlcluase = "{}={}".format(wherecluase,seg[0] - 1)
            # print(wherecluase)
            except Exception as e:
                print("Cannot create wherecluase")
                print(e)

            try:
                upcursor = arcpy.da.UpdateCursor(Temp_Splited_simplify_cl,fieldNames,sqlcluase)
            except Exception as e:
                print(e)
                print("Cannot create UpdateCursor for simple CL {}".format(seg[0]))
            # arcpy.SelectLayerByAttribute_management(split_simCL, "CLEAR_SELECTION", sqlcluase)
            try:
                for row in upcursor:

                    row[1] = seg[1]
                    row[2] = seg[2]
                    row[3] = seg[3]
                    row[4] = seg[4]
                    if seg[1] != 0 and seg[3] != 0:
                        row[5] = "Left, Right"
                    elif seg[2] == None and seg[4] != 0:
                        row[5] = "Right"
                    elif seg[2] != 0 and seg[4] == None:
                        row[5] = "Left"
                    else:
                        row[5] = "None"

                    row[6] = (seg[3] + seg[4]) / 2

                    upcursor.updateRow(row)
                    print("Updating Simplified CL: {}".format(seg[0]))

                del upcursor
            except Exception as e:
                print(e)
                print("Cannot Update simpCL for simple CL {}".format(seg[0]))
    pool.close()
    pool.join()

    All_buffer_simCl = r"memory/buffer_simCL"
    arcpy.Buffer_analysis(Temp_Splited_simplify_cl,All_buffer_simCl, "2.0 Meters", "FULL", "FLAT", "NONE",  None, "PLANAR")

#    arcpy.SpatialJoin_analysis(before_updated_Percentile_CL, All_buffer_simCl,Percentile_CL,
#                           "JOIN_ONE_TO_MANY", "KEEP_ALL",None,"WITHIN_CLEMENTINI", None, '')
    arcpy.SpatialJoin_analysis(before_updated_Percentile_CL, All_buffer_simCl,Percentile_CL,
                               "JOIN_ONE_TO_MANY", "KEEP_ALL",None, "CLOSEST", "0.3 Meters", '')
    print("Updating Percentile Statistic into CL attributes Done.")

    Percentile_SimplifiedCL = os.path.abspath(os.path.dirname(Output_Footprint) + "/" \
                                 + os.path.basename(Centerline_Feature_Class).rpartition('.')[
                                     0] + ProcMode+ "_Percentile_SimplifiedCL.shp")

    arcpy.CopyFeatures_management(Temp_Splited_simplify_cl, Percentile_SimplifiedCL)
    arcpy.Delete_management(Temp_Splited_simplify_cl)

    Splited_Updated_Percentilecl=r"memory/updated_Percentile_CL"
    arcpy.CopyFeatures_management(Percentile_CL,Splited_Updated_Percentilecl)
    # arcpy.Delete_management("split_simplified_CL_Lay")
    return Splited_Updated_Percentilecl


def main(argv=None):
    # Setup script path and workspace folder
    workspaceName = "FLM_DLFP_output"
    global outWorkspace
    outWorkspace = flmc.SetupWorkspace_2(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_DLFP_params.txt")

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
    global Search_R
    Search_R = args[6].rstrip()
    global Canopy_Percentile
    Canopy_Percentile = args[7].rstrip()
    global CanopyTh_Percent
    CanopyTh_Percent = args[8].rstrip()
    global TreeSearchRadius
    TreeSearchRadius = float(args[9].rstrip())
    global MaximumLineDistance
    MaximumLineDistance = float(args[10].rstrip())
    global CanopyAvoidance
    CanopyAvoidance = float(args[11].rstrip())
    global CostRasterExponent
    CostRasterExponent = float(args[12].rstrip())

    global Corridor_Threshold_Field
    Canopy_Threshold_option = args[3].rstrip()
    Corridor_Threshold_Field = "CorridorTh"
    Canopy_Threshold_Field = "CanTh_HtM"

    f = open(outWorkspace + "\\params.txt", "w")
    f.write(Centerline_Feature_Class + "\n")
    f.write(CHM_Raster + "\n")
    f.write(str(Maximum_distance_from_centerline) + "\n")
    f.write(Expand_And_Shrink_Cell_Range + "\n")
    f.write(str(ProcessSegments) + "\n")
    f.write(Output_Footprint + "\n")
    f.write(Search_R + "\n")
    f.write(Canopy_Percentile + "\n")
    f.write(CanopyTh_Percent + "\n")
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
        print(e)

    Updated_CL_fc = Percentile_Call(workspaceName, outWorkspace, Centerline_Feature_Class, Output_Footprint, CHM_Raster,
                                  Search_R, Canopy_Percentile, CanopyTh_Percent, ProcessSegments,
                                  TreeSearchRadius, MaximumLineDistance, CanopyAvoidance, CostRasterExponent)

    segment_all_Cal_DynCC=[]
    print("Preparing lines for Dynamic Footprint........")
    with arcpy.da.SearchCursor(Updated_CL_fc,["OID@","SHAPE@","CanTh_HtM"]) as sCursor:
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
        ft_list = []
        for sublist in footprints:
            if sublist:
                for item in sublist:
                    if item:
                        ft_list.append(item)

        fileMerge = outWorkspace + "\\FLM_LFP_Merge.shp"
        arcpy.Merge_management(ft_list, fileMerge)
        arcpy.Dissolve_management(fileMerge, Output_Footprint)
        arcpy.Delete_management(fileMerge)
    except Exception as e:
        print(e)

    flmc.logStep("Footprints merged.")
    arcpy.CheckInExtension("Spatial")
    arcpy.CheckInExtension("3D")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    input("<Press any key to exit>")
