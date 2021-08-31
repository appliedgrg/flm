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
# SLM_Attribute_Functions.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: This script contains common functions used by FLM attribution
# tools. Of special importance is the FlmLineSplit function which prepares
# an input polyline shapefile for attribution.
#
# ---------------------------------------------------------------------------

import arcpy
import FLM_Common as flmc


def PathFile(path):
    return path[path.rfind("\\") + 1:]


def FlmLineSplit(workspace, Input_Lines, SamplingType, Segment_Length, Tolerance_Radius):
    if SamplingType == "IN-FEATURES":
        return Input_Lines

    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = True

    FLA_Line_Unsplit = workspace + "\\FLA_Line_Unsplit.shp"
    FLA_Line_Unsplit_Single = workspace + "\\FLA_Line_Unsplit_Single.shp"
    FLA_Line_Split_Vertices = workspace + "\\FLA_Line_Split_Vertices.shp"
    FLA_Segmented_Lines = workspace + "\\FLA_Segmented_Lines.shp"

    flmc.log("FlmLineSplit: Executing UnsplitLine")
    flmc.log("Input_Lines: " + Input_Lines)
    flmc.log("FLA_Line_Unsplit: " + FLA_Line_Unsplit)

    arcpy.UnsplitLine_management(Input_Lines, FLA_Line_Unsplit)
    arcpy.MultipartToSinglepart_management(FLA_Line_Unsplit, FLA_Line_Unsplit_Single)
    arcpy.Delete_management(FLA_Line_Unsplit)

    if SamplingType == "ARBITRARY":
        arcpy.GeneratePointsAlongLines_management(FLA_Line_Unsplit_Single, FLA_Line_Split_Vertices, "DISTANCE",
                                                  Segment_Length, "", "NO_END_POINTS")
    elif SamplingType == "LINE-CROSSINGS":
        arcpy.Intersect_analysis(PathFile(FLA_Line_Unsplit_Single), PathFile(FLA_Line_Split_Vertices),
                                 join_attributes="ALL", cluster_tolerance=Tolerance_Radius, output_type="POINT")

    if SamplingType != "WHOLE-LINE":  # "ARBITRARY" or "LINE-CROSSINGS"
        arcpy.SplitLineAtPoint_management(FLA_Line_Unsplit_Single, FLA_Line_Split_Vertices, FLA_Segmented_Lines,
                                          Tolerance_Radius)
        arcpy.Delete_management(FLA_Line_Unsplit_Single)
        arcpy.Delete_management(FLA_Line_Split_Vertices)
    else:  # "WHOLE-LINE"
        FLA_Segmented_Lines = FLA_Line_Unsplit_Single

    return FLA_Segmented_Lines
