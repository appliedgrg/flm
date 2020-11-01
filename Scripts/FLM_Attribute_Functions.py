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
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: This script contains common functions used by SLM attribution
# tools. Of special importance is the SlmLineSplit function which prepares
# an input polyline shapefile for attribution.
#
# ---------------------------------------------------------------------------

import arcpy
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")
from . import SLM_Common as slmc

def PathFile(path):
	return path[path.rfind("\\")+1:]

def SlmLineSplit(workspace, Input_Lines,SamplingType,Segment_Length,Tolerance_Radius):

	if (SamplingType == "IN-FEATURES"):
		return Input_Lines
		
	arcpy.env.workspace = workspace
	SLA_Line_Unsplit = workspace+"\\SLA_Line_Unsplit.shp"
	SLA_Line_Unsplit_Single = workspace+"\\SLA_Line_Unsplit_Single.shp"
	SLA_Line_Split_Vertices = workspace+"\\SLA_Line_Split_Vertices.shp"
	SLA_Segmented_Lines = workspace+"\\SLA_Segmented_Lines.shp"
	
	arcpy.UnsplitLine_management(Input_Lines,SLA_Line_Unsplit)
	arcpy.MultipartToSinglepart_management(SLA_Line_Unsplit,SLA_Line_Unsplit_Single)
	arcpy.Delete_management(SLA_Line_Unsplit)

	if (SamplingType == "ARBITRARY"):
		arcpy.GeneratePointsAlongLines_management(SLA_Line_Unsplit_Single, SLA_Line_Split_Vertices, "DISTANCE", Segment_Length, "", "NO_END_POINTS")
	elif (SamplingType == "LINE-CROSSINGS"):
		arcpy.Intersect_analysis( PathFile(SLA_Line_Unsplit_Single),  PathFile(SLA_Line_Split_Vertices), join_attributes="ALL", cluster_tolerance=Tolerance_Radius, output_type="POINT")
		
	if (SamplingType != "WHOLE-LINE"):
		arcpy.SplitLineAtPoint_management(SLA_Line_Unsplit_Single, SLA_Line_Split_Vertices, SLA_Segmented_Lines, Tolerance_Radius)
		arcpy.Delete_management(SLA_Line_Unsplit_Single)
		arcpy.Delete_management(SLA_Line_Split_Vertices)
	else:
		SLA_Segmented_Lines = SLA_Line_Unsplit_Single
	
	return SLA_Segmented_Lines