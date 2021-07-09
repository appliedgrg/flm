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
# FLM_ForestLineAttributes.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Calculates a series of attributes related to forest line shape, 
# size and microtopography.
#
# ---------------------------------------------------------------------------

import multiprocessing
import math
import arcpy
arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc
import FLM_Attribute_Functions as flma 

workspaceName = "FLM_SLA_output"

def workLines(lineNo):
	outWorkspace = flmc.GetWorkspace(workspaceName)
	f = open(outWorkspace + "\\params.txt")
	outWorkspace = f.readline().strip()
	Input_Lines = f.readline().strip()
	Input_Footprint = f.readline().strip()
	Input_CHM = f.readline().strip()
	SamplingType = f.readline().strip()
	Segment_Length = float(f.readline().strip())
	Tolerance_Radius = float(f.readline().strip())
	LineSearchRadius = float(f.readline().strip())
	Attributed_Segments = f.readline().strip()
	areaAnalysis = True if f.readline().strip() == "True" else False
	heightAnalysis = True if  f.readline().strip() == "True" else False
	f.close()

	#Temporary files
	lineSeg = outWorkspace +"\\FLM_SLA_Segment_" + str(lineNo) +".shp"
	#fileFoot = outWorkspace +"\\FLM_SLA_Split_" + str(lineNo) +".shp"
	lineBuffer = outWorkspace +"\\FLM_SLA_Buffer_" + str(lineNo) +".shp"
	lineClip = outWorkspace+"\\FLM_SLA_Clip_" + str(lineNo) +".shp"
	#fileFoot = outWorkspace+"\\FLM_SLA_Foot_" + str(lineNo) +".shp"
	lineStats = outWorkspace+"\\FLM_SLA_Stats_" + str(lineNo) +".dbf"
	
	"""
	arcpy.AddField_management(lineSeg,"Direction","TEXT")
	arcpy.AddField_management(lineSeg,"Sinuosity","DOUBLE")

	if(areaAnalysis):
		arcpy.AddField_management(lineSeg,"AvgWidth","DOUBLE")
		arcpy.AddField_management(lineSeg,"Fragment","DOUBLE")
		if(heightAnalysis):
			arcpy.AddField_management(lineSeg,"AvgHeight","DOUBLE")
			arcpy.AddField_management(lineSeg,"Volume","DOUBLE")
			arcpy.AddField_management(lineSeg,"Roughness","DOUBLE")
	"""
	
	if(areaAnalysis):

		arcpy.Buffer_analysis(lineSeg, lineBuffer, LineSearchRadius, line_side="FULL", line_end_type="FLAT", dissolve_option="NONE", dissolve_field="", method="PLANAR")
		arcpy.Clip_analysis(Input_Footprint, lineBuffer, lineClip)
		arcpy.Delete_management(lineBuffer)
		if (heightAnalysis and arcpy.Exists(lineClip)):
			try:
				arcpy.gp.ZonalStatisticsAsTable_sa(lineClip, arcpy.Describe(lineClip).OIDFieldName, Input_CHM, lineStats, "DATA", "ALL")
			except:
				lineStats = ""
	
	rows = arcpy.UpdateCursor(lineSeg)
	shapeField = arcpy.Describe(lineSeg).ShapeFieldName
	row = rows.next()

	feat = row.getValue(shapeField)   #creates a geometry object
	length = float(row.getValue("LENGTH"))   #creates a geometry object
	
	try:
		bearing = float(row.getValue("BEARING"))   #creates a geometry object
	except:
		bearing = 0
		
	segmentnum = 0
	segment_list = []
	for segment in feat: #loops through every segment in a line
		#loops through every vertex of every segment
		for pnt in feat.getPart(segmentnum):                 #get.PArt returns an array of points for a particular part in the geometry
			if pnt:                  #adds all the vertices to segment_list, which creates an array
				segment_list.append(arcpy.Point(float(pnt.X), float(pnt.Y)))
	
	#Sinuosity calculation			
	eucDistance = arcpy.PointGeometry(feat.firstPoint).distanceTo(arcpy.PointGeometry(feat.lastPoint))
	try:
		row.setValue("Sinuosity",length/eucDistance)
	except:
		row.setValue("Sinuosity",float("inf"))
		
	#Direction based on bearing
	ori = "N-S"
	if ((bearing >= 22.5 and bearing < 67.5) or (bearing >= 202.5 and bearing < 247.5)):
		ori = "NE-SW"
	elif ((bearing >= 67.5 and bearing < 112.5) or (bearing >= 247.5 and bearing < 292.5)):
		ori = "E-W"
	elif ((bearing >= 112.5 and bearing < 157.5) or (bearing >= 292.5 and bearing < 337.5)):
		ori = "NW-SE"
	row.setValue("Direction",ori)

	#If footprint polygons are available, get area-based variables
	if(areaAnalysis):
		totalArea = float(row.getValue("POLY_AREA"))
		totalPerim = float(row.getValue("PERIMETER"))
		
		row.setValue("AvgWidth",totalArea/length)
	
		try:
			row.setValue("Fragment",totalPerim/totalArea)
		except:
			row.setValue("Fragment",float("inf"))
		
		if(arcpy.Exists(lineStats)):

			#Retrieve useful stats from table which are used to derive CHM attributes
			ChmFootprintCursor = arcpy.SearchCursor(lineStats)
			ChmFoot = ChmFootprintCursor.next()
			chm_count = float(ChmFoot.getValue("COUNT"))
			chm_area = float(ChmFoot.getValue("AREA"))
			chm_mean = float(ChmFoot.getValue("MEAN"))
			chm_std = float(ChmFoot.getValue("STD"))
			chm_sum = float(ChmFoot.getValue("SUM"))
			del ChmFootprintCursor
			
			#Average vegetation height directly obtained from CHM mean
			row.setValue("AvgHeight",chm_mean)
			#Cell area obtained via dividing the total area by the number of cells (this assumes that the projection is UTM to obtain a measure in square meters)
			cellArea = chm_area/chm_count
			#CHM volume (3D) is obtained via multiplying the sum of height (1D) of all cells within the footprint by the area of each cell (2D)
			row.setValue("Volume",chm_sum*cellArea)
			#The following math is performed to use available stats (fast) and avoid further raster sampling procedures (slow)
			#RMSH is equal to the square root of the sum of the squared mean and the squared standard deviation (population)
			#STD of population (n) is derived from the STD of sample (n-1). This number is not useful by itself, only to derive RMSH.
			sqStdPop = math.pow(chm_std,2)*(chm_count-1)/chm_count
			#Obtain RMSH from mean and STD
			row.setValue("Roughness",math.sqrt(math.pow(chm_mean,2)+sqStdPop))

	rows.updateRow(row)

	del row, rows
	#Clean temporary files
	"""
	if(arcpy.Exists(fileBuffer)):
		arcpy.Delete_management(fileBuffer)
	if(arcpy.Exists(lineClip)):
		arcpy.Delete_management(lineClip)
	"""
	if(arcpy.Exists(lineClip)):
		arcpy.Delete_management(lineClip)
	if(arcpy.Exists(lineStats)):
		arcpy.Delete_management(lineStats)

def main(argv=None):
	# Setup script path and workspace folder
	global outWorkspace
	outWorkspace = flmc.SetupWorkspace(workspaceName)
	#outWorkspace = flmc.GetWorkspace(workspaceName)
	arcpy.env.workspace = outWorkspace
	arcpy.env.overwriteOutput = True

	# Load arguments from file
	if argv:
		args = argv
	else:
		args = flmc.GetArgs("FLM_FLA_params.txt")

	# Tool arguments
	Input_Lines = args[0].rstrip()
	Input_Footprint = args[1].rstrip()
	Input_CHM = args[2].rstrip()
	SamplingType = args[3].rstrip()
	Segment_Length = float(args[4].rstrip())
	Tolerance_Radius = float(args[5].rstrip())
	LineSearchRadius = float(args[6].rstrip())
	Attributed_Segments = args[7].rstrip()

	areaAnalysis = arcpy.Exists(Input_Footprint)
	heightAnalysis = arcpy.Exists(Input_CHM)

	# write params to text file
	f = open(outWorkspace + "\\params.txt", "w")
	f.write(outWorkspace + "\n")
	f.write(Input_Lines + "\n")
	f.write(Input_Footprint + "\n")
	f.write(Input_CHM + "\n")
	f.write(SamplingType + "\n")
	f.write(str(Segment_Length) + "\n")
	f.write(str(Tolerance_Radius) + "\n")
	f.write(str(LineSearchRadius) + "\n")
	f.write(Attributed_Segments + "\n")
	f.write(str(areaAnalysis) + "\n")
	f.write(str(heightAnalysis) + "\n")
	f.close()

	# Temporary layers
	fileBuffer = outWorkspace + "\\FLM_SLA_Buffer.shp"
	fileIdentity = outWorkspace + "\\FLM_SLA_Identity.shp"
	fileFootprints = outWorkspace + "\\FLM_SLA_Footprints.shp"

	footprintField = flmc.FileToField(fileBuffer)
	
	flmc.log("Preparing line segments...")
	# Segment lines
	flmc.log("FlmLineSplit: Input_Lines = " + Input_Lines)
	SLA_Segmented_Lines = flma.FlmLineSplit(outWorkspace, Input_Lines, SamplingType, Segment_Length, Tolerance_Radius)
	flmc.logStep("Line segmentation")

	# Linear attributes
	flmc.log("Adding attributes...")
	arcpy.AddGeometryAttributes_management(SLA_Segmented_Lines, "LENGTH;LINE_BEARING", "METERS")
	
	if(areaAnalysis):
		arcpy.Buffer_analysis(SLA_Segmented_Lines, fileBuffer, LineSearchRadius, line_side="FULL", line_end_type="FLAT", dissolve_option="NONE", dissolve_field="", method="PLANAR")
		arcpy.Identity_analysis(Input_Footprint, fileBuffer, fileIdentity, join_attributes="ONLY_FID", cluster_tolerance="", relationship="NO_RELATIONSHIPS")
		arcpy.Dissolve_management(fileIdentity, fileFootprints, dissolve_field=footprintField, statistics_fields="", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
		arcpy.JoinField_management(fileFootprints, footprintField, fileBuffer, arcpy.Describe(fileBuffer).OIDFieldName, fields="ORIG_FID")
		fCursor = arcpy.UpdateCursor(fileFootprints)
		for row in fCursor:
			if float(row.getValue(footprintField)) < 0:
				fCursor.deleteRow(row)
		del fCursor
		#arcpy.CalculateField_management(fileFootprints, footprintField, expression="!"+footprintField+"! -1", expression_type="PYTHON_9.3", code_block="")
		arcpy.AddGeometryAttributes_management(fileFootprints, Geometry_Properties="AREA;PERIMETER_LENGTH", Length_Unit="METERS", Area_Unit="SQUARE_METERS", Coordinate_System="")
		arcpy.JoinField_management(SLA_Segmented_Lines, arcpy.Describe(SLA_Segmented_Lines).OIDFieldName, fileFootprints, "ORIG_FID", fields="POLY_AREA;PERIMETER")
		#flmc.SplitFeature(fileFootprints,footprintField,outWorkspace, "SLA")
		
		arcpy.Delete_management(fileBuffer)
		arcpy.Delete_management(fileIdentity)
		arcpy.Delete_management(fileFootprints)
		
	
	# Add other fields
	keepFields = ["LENGTH","BEARING"]
	if(areaAnalysis):
		keepFields += ["POLY_AREA","PERIMETER"]
		
	arcpy.AddField_management(SLA_Segmented_Lines,"Direction","TEXT")
	arcpy.AddField_management(SLA_Segmented_Lines,"Sinuosity","DOUBLE")
	keepFields += ["Direction","Sinuosity"]
	
	if(areaAnalysis):
		arcpy.AddField_management(SLA_Segmented_Lines,"AvgWidth","DOUBLE")
		arcpy.AddField_management(SLA_Segmented_Lines,"Fragment","DOUBLE")
		keepFields += ["AvgWidth","Fragment"]
		if(heightAnalysis):
			arcpy.AddField_management(SLA_Segmented_Lines,"AvgHeight","DOUBLE")
			arcpy.AddField_management(SLA_Segmented_Lines,"Volume","DOUBLE")
			arcpy.AddField_management(SLA_Segmented_Lines,"Roughness","DOUBLE")
			keepFields += ["AvgHeight","Volume","Roughness"]
	
	# Prepare input lines for multiprocessing
	numLines = flmc.SplitLines(SLA_Segmented_Lines, outWorkspace, "SLA", False, keepFields ) #,"Direction","Sinuosity","Area","AvgWidth","Perimeter","Fragment","SLA_Unity","AvgHeight","Volume","Roughness"])
	
	arcpy.Delete_management(SLA_Segmented_Lines)
	
	pool = multiprocessing.Pool(processes=flmc.GetCores())
	flmc.log("Multiprocessing lines...")
	pool.map(workLines, range(1,numLines+1))
	pool.close()
	pool.join()
	
	flmc.logStep("Line multiprocessing")
	
	flmc.log("Merging lines...")
	tempShapefiles = arcpy.ListFeatureClasses()
	
	arcpy.Merge_management(tempShapefiles,Attributed_Segments)

	flmc.logStep("Merging")
		
	for shp in tempShapefiles:
		arcpy.Delete_management(shp)
