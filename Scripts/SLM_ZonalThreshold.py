# ---------------------------------------------------------------------------
#
# SLM_ZonalThreshold.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: Assigns corridor thresholds to the input lines based on their 
# surrounding canopy density
#
# ---------------------------------------------------------------------------

import multiprocessing
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
from . import SLM_Common as slmc

# Setup script path and workspace folder
workspaceName = "SLM_ZT_output"
outWorkspace = slmc.GetWorkspace(workspaceName)
arcpy.env.workspace = outWorkspace
arcpy.env.overwriteOutput = True

# Load arguments from file
args = slmc.GetArgs("SLM_ZT_params.txt")

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
	fileSeg = outWorkspace +"\\SLM_ZT_Segment_" + str(lineNo) +".shp"
	fileBuffer = outWorkspace +"\\SLM_ZT_Buffer_" + str(lineNo) +".shp"
	fileZonal = outWorkspace +"\\SLM_ZT_Zonal_" + str(lineNo) +".dbf"

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
	outWorkspace = slmc.SetupWorkspace(workspaceName)

	# Prepare input lines for multiprocessing
	numLines = slmc.SplitLines(Input_Feature_Class, outWorkspace, "ZT", False, ThresholdField)
	
	pool = multiprocessing.Pool(processes=slmc.GetCores())
	slmc.log("Multiprocessing line zonal thresholds...")
	pool.map(workLines, range(1,numLines+1))
	pool.close()
	pool.join()
	
	slmc.logStep("Line multiprocessing")
	
	slmc.log("Merging layers...")
	tempShapefiles = arcpy.ListFeatureClasses()
	
	arcpy.Merge_management(tempShapefiles,OutputLines)


	slmc.logStep("Merge")
		
	for shp in tempShapefiles:
		arcpy.Delete_management(shp)
	
