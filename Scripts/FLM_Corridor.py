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
# SLM_Corridor.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: Creates a least cost corridor raster between vertices of the input
# lines. This step can be skipped with the 'Line Footprint' tool.
#
# ---------------------------------------------------------------------------

import os
import multiprocessing
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
from . import SLM_Common as slmc
import math

# Setup script path and workspace folder
workspaceName = "SLM_CO_output"
outWorkspace = slmc.GetWorkspace(workspaceName)
arcpy.env.workspace = outWorkspace
arcpy.env.overwriteOutput = True

# Load arguments from file
args = slmc.GetArgs("SLM_CO_params.txt")

# Tool arguments
Centerline_Feature_Class = args[0].rstrip()
Canopy_Raster = args[1].rstrip()
Cost_Raster = args[2].rstrip()
Maximum_distance_from_centerline = float(args[3].rstrip()) / 2.0
ProcessSegments = args[4].rstrip()=="True"
Output_Corridor = args[5].rstrip()

def PathFile(path):
	return path[path.rfind("\\")+1:]
	
def workLines(lineNo):
	#Temporary files
	fileSeg = outWorkspace +"\\SLM_CO_Segment_" + str(lineNo) +".shp"
	fileOrigin = outWorkspace +"\\SLM_CO_Origin_" + str(lineNo) +".shp"
	fileDestination = outWorkspace +"\\SLM_CO_Destination_" + str(lineNo) +".shp"
	fileBuffer = outWorkspace +"\\SLM_CO_Buffer_" + str(lineNo) +".shp"
	fileClip = outWorkspace+"\\SLM_CO_Clip_" + str(lineNo) +".tif"
	fileCostDa = outWorkspace+"\\SLM_CO_CostDa_" + str(lineNo) +".tif"
	fileCostDb = outWorkspace+"\\SLM_CO_CostDb_" + str(lineNo) +".tif"
	fileCorridor = outWorkspace+"\\SLM_CO_Corridor_" + str(lineNo) +".tif"
	fileCorridorMin = outWorkspace+"\\SLM_CO_CorridorMin_" + str(lineNo) +".tif"
	
	
	# Load segment list
	segment_list = []
	rows = arcpy.SearchCursor(fileSeg)
	shapeField = arcpy.Describe(fileSeg).ShapeFieldName
	for row in rows:
		feat = row.getValue(shapeField)   #creates a geometry object
		segmentnum = 0
		for segment in feat: #loops through every segment in a line
			#loops through every vertex of every segment
			for pnt in feat.getPart(segmentnum):                 #get.PArt returns an array of points for a particular part in the geometry
				if pnt:                  #adds all the vertices to segment_list, which creates an array
					segment_list.append(arcpy.Point(float(pnt.X), float(pnt.Y)))

			segmentnum += 1
	del rows

	# Find origin and destination coordinates
	x1 = segment_list[0].X
	y1 = segment_list[0].Y
	x2 = segment_list[-1].X
	y2 = segment_list[-1].Y

	# Create origin feature class
	arcpy.CreateFeatureclass_management(outWorkspace,PathFile(fileOrigin),"POINT",Centerline_Feature_Class,"DISABLED","DISABLED",Centerline_Feature_Class)
	cursor = arcpy.da.InsertCursor(fileOrigin, ["SHAPE@XY"])
	xy = (float(x1),float(y1))
	cursor.insertRow([xy])
	del cursor
	
	# Create destination feature class
	arcpy.CreateFeatureclass_management(outWorkspace,PathFile(fileDestination),"POINT",Centerline_Feature_Class,"DISABLED","DISABLED",Centerline_Feature_Class)
	cursor = arcpy.da.InsertCursor(fileDestination, ["SHAPE@XY"])
	xy = (float(x2),float(y2))
	cursor.insertRow([xy])
	del cursor
	
	# Buffer around line
	arcpy.Buffer_analysis(fileSeg, fileBuffer, Maximum_distance_from_centerline, "FULL", "ROUND", "NONE", "", "PLANAR")

	# Clip cost raster using buffer
	DescBuffer = arcpy.Describe(fileBuffer)
	SearchBox = str(DescBuffer.extent.XMin)+" "+str(DescBuffer.extent.YMin)+" "+str(DescBuffer.extent.XMax)+" "+str(DescBuffer.extent.YMax)
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
	RasterCorridor = (RasterCorridor-CorrMin)
	RasterCorridor.save(fileCorridorMin)
	del RasterCorridor

	#Clean temporary files
	arcpy.Delete_management(fileSeg)
	arcpy.Delete_management(fileBuffer)
	arcpy.Delete_management(fileOrigin)
	arcpy.Delete_management(fileDestination)
	arcpy.Delete_management(fileClip)
	arcpy.Delete_management(fileCostDa)
	arcpy.Delete_management(fileCostDb)
	arcpy.Delete_management(fileCorridor)
	
def workMerge(workerNo):
	# Worker 1 will merge files 1 and 2; worker 2 will merge files 3 and 4; and so on...
	fileCorridorMinA = outWorkspace+"\\SLM_CO_CorridorMin_" + str(workerNo*2-1) +".tif"
	fileCorridorMinB = outWorkspace+"\\SLM_CO_CorridorMin_" + str(workerNo*2) +".tif"
	# Add an underline at the end of the name, so that it does not overwrite an existing file
	outMergeName = outWorkspace+"\\SLM_CO_CorridorMin_" + str(workerNo) +"_.tif"
	if arcpy.Exists(fileCorridorMinB):
		arcpy.MosaicToNewRaster_management([fileCorridorMinA,fileCorridorMinB],outWorkspace,PathFile(outMergeName), "", "32_BIT_FLOAT", "", "1", "MINIMUM", "MATCH")
		#Clean old files
		arcpy.Delete_management(fileCorridorMinA)
		arcpy.Delete_management(fileCorridorMinB)
	else:
		arcpy.Rename_management(fileCorridorMinA,PathFile(outMergeName))
	
def renameMergedFiles(fileWorkspace):
	arcpy.env.workspace = fileWorkspace
	rasters = arcpy.ListRasters()
	for ras in rasters:
		arcpy.Rename_management(PathFile(ras),PathFile(ras[:ras.rfind("_")]+ras[ras.rfind("_")+1:]))
	del rasters

def main():
	global outWorkspace
	outWorkspace = slmc.SetupWorkspace(workspaceName)

	# Prepare input lines for multiprocessing
	numLines = slmc.SplitLines(Centerline_Feature_Class, outWorkspace, "CO", ProcessSegments)
	
	pool = multiprocessing.Pool(processes=slmc.GetCores())
	slmc.log("Multiprocessing line corridors...")
	pool.map(workLines, range(1,numLines+1))
	pool.close()
	pool.join()
	
	slmc.logStep("Corridor multiprocessing")
	
	nRasters = len(arcpy.ListRasters())
	
	if (nRasters==1):
		arcpy.CopyRaster_management(arcpy.ListRasters()[0],Output_Corridor)
	else:
		mergeLoops = 0
		slmc.log("Merging corridor rasters...")
		while nRasters>1:
			slmc.log("Multiprocessing line corridors... Round "+str(mergeLoops+1)+"; "+str(nRasters)+" rasters in output folder to process...")
			# Multiprocessing merge, so that every process merges two files at a time
			pool = multiprocessing.Pool(processes=slmc.GetCores())
			
			# Create a number of workers equal to half the number of rasters, rounded up
			pool.map(workMerge, range(1,int(math.ceil(nRasters/2.0)+1)))
			pool.close()
			pool.join()
			
			renameMergedFiles(outWorkspace)
			nRasters = len(arcpy.ListRasters())
			
			# Log round execution time
			slmc.logStep("Merge Round "+str(mergeLoops+1))
			
			# Prevent merging process from becoming an infinite loop
			mergeLoops+=1
			
			if(mergeLoops>10 or nRasters<5):
				corridorRasters = arcpy.ListRasters()
				slmc.log("Merging remaining "+str(nRasters)+" files in a single process...")
				arcpy.MosaicToNewRaster_management(corridorRasters,os.path.dirname(Output_Corridor),os.path.basename(Output_Corridor), "", "32_BIT_FLOAT", "", "1", "MINIMUM", "MATCH")
				slmc.log("Deleting temporary files...")
				for ras in corridorRasters:
					arcpy.Delete_management(ras)
				# Log round execution time
				slmc.logStep("Merge Final Round")
				break
		
if __name__ == '__main__':
	main()