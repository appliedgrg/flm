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
# FLM_ZonalThreshold.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Assigns corridor thresholds to the input lines based on their 
# surrounding canopy density
#
# ---------------------------------------------------------------------------

import multiprocessing
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

# Setup script path and workspace folder
workspaceName = "FLM_ZT_output"
outWorkspace = flmc.GetWorkspace(workspaceName)
arcpy.env.workspace = outWorkspace
arcpy.env.overwriteOutput = True

# Load arguments from file
args = flmc.GetArgs("FLM_ZT_params.txt")

# Tool arguments
Input_Feature_Class = args[0].rstrip()
#ID_Field = args[1].rstrip()
ThresholdField = args[1].rstrip()
Canopy_Raster = args[2].rstrip()
Canopy_Search_Radius = float(args[3].rstrip())
MinValue = float(args[4].rstrip())
MaxValue = float(args[5].rstrip())
OutputLines = args[6].rstrip()


def workLines(lineNo):
	#Temporary files
	fileSeg = outWorkspace +"\\FLM_ZT_Segment_" + str(lineNo) +".shp"
	fileBuffer = outWorkspace +"\\FLM_ZT_Buffer_" + str(lineNo) +".shp"
	fileZonal = outWorkspace +"\\FLM_ZT_Zonal_" + str(lineNo) +".dbf"

	arcpy.Buffer_analysis(fileSeg, fileBuffer, Canopy_Search_Radius, "FULL", "ROUND", "NONE", "", "PLANAR")	

	ZonalStatisticsAsTable(fileBuffer,"ORIG_FID",Canopy_Raster,fileZonal,"DATA","MEAN")

	"""
	difCount = int(arcpy.GetCount_management(Input_Feature_Class).getOutput(0))-int(arcpy.GetCount_management(fileZonal).getOutput(0))
	if (difCount!= 0):
		arcpy.AddWarning("Warning! "+str(difCount)+" records from your input lines are missing from the zonal analysis.")
		arcpy.AddMessage("This is ikely due to small lines being overlapped by bigger lines.")
		arcpy.AddMessage("The original value (default of 8.0) will be retained for those records.")
	"""
	
	zonal = []
	zoTable = arcpy.SearchCursor(fileZonal)
	for row in zoTable:
		zonal.append([int(row.getValue("ORIG_FID")),float(row.getValue("MEAN"))])
	del zoTable
	
	line = 0
	cursor = arcpy.UpdateCursor(fileSeg)
	for row in cursor:
		"""
		if ((zonal[line][0]) != int(row.getValue(ID_Field))):
			arcpy.AddWarning("Missing record FID "+str(int(row.getValue(ID_Field))))
			continue
		"""
		threshold = MinValue + (zonal[line][1]*zonal[line][1]) * (MaxValue - MinValue)
		row.setValue(ThresholdField, threshold)
		cursor.updateRow(row)
		line += 1
	del cursor
	
	arcpy.Delete_management(fileBuffer)
	arcpy.Delete_management(fileZonal)

def main():	
	global outWorkspace
	outWorkspace = flmc.SetupWorkspace(workspaceName)

	# Prepare input lines for multiprocessing
	numLines = flmc.SplitLines(Input_Feature_Class, outWorkspace, "ZT", False, ThresholdField)
	
	pool = multiprocessing.Pool(processes=flmc.GetCores())
	flmc.log("Multiprocessing line zonal thresholds...")
	pool.map(workLines, range(1,numLines+1))
	pool.close()
	pool.join()
	
	flmc.logStep("Line multiprocessing")
	
	flmc.log("Merging layers...")
	tempShapefiles = arcpy.ListFeatureClasses()
	
	arcpy.Merge_management(tempShapefiles,OutputLines)


	flmc.logStep("Merge")
		
	for shp in tempShapefiles:
		arcpy.Delete_management(shp)
	
