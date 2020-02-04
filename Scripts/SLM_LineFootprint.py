# ---------------------------------------------------------------------------
#
# SLM_LineFootprint.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: Creates footprint polygons for each input line based on a least 
# cost corridor method and individual line thresholds.
#
# ---------------------------------------------------------------------------

import multiprocessing
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
from . import SLM_Common as slmc

# Setup script path and workspace folder
workspaceName = "SLM_LFP_output"
outWorkspace = slmc.GetWorkspace(workspaceName)
arcpy.env.workspace = outWorkspace
arcpy.env.overwriteOutput = True

# Load arguments from file
args = slmc.GetArgs("SLM_LFP_params.txt")

# Tool arguments
Centerline_Feature_Class = args[0].rstrip()
Canopy_Raster = args[1].rstrip()
Cost_Raster = args[2].rstrip()
Corridor_Threshold_Field = args[3].rstrip()
Maximum_distance_from_centerline = float(args[4].rstrip())  / 2.0
Expand_And_Shrink_Cell_Range = args[5].rstrip()
ProcessSegments = args[6].rstrip()=="True"
Output_Footprint = args[7].rstrip()

def PathFile(path):
	return path[path.rfind("\\")+1:]
	
def workLines(lineNo):
	#Temporary files
	fileSeg = outWorkspace +"\\SLM_LFP_Segment_" + str(lineNo) +".shp"
	fileOrigin = outWorkspace +"\\SLM_LFP_Origin_" + str(lineNo) +".shp"
	fileDestination = outWorkspace +"\\SLM_LFP_Destination_" + str(lineNo) +".shp"
	fileBuffer = outWorkspace +"\\SLM_LFP_Buffer_" + str(lineNo) +".shp"
	fileClip = outWorkspace+"\\SLM_LFP_Clip_" + str(lineNo) +".tif"
	fileCostDa = outWorkspace+"\\SLM_LFP_CostDa_" + str(lineNo) +".tif"
	fileCostDb = outWorkspace+"\\SLM_LFP_CostDb_" + str(lineNo) +".tif"
	fileCorridor = outWorkspace+"\\SLM_LFP_Corridor_" + str(lineNo) +".tif"
	fileCorridorMin = outWorkspace+"\\SLM_LFP_CorridorMin_" + str(lineNo) +".tif"
	fileThreshold = outWorkspace+"\\SLM_LFP_Threshold_" + str(lineNo) +".tif"
	fileExpand = outWorkspace+"\\SLM_LFP_Expand_" + str(lineNo) +".tif"
	fileShrink = outWorkspace+"\\SLM_LFP_Shrink_" + str(lineNo) +".tif"
	fileClean = outWorkspace+"\\SLM_LFP_Clean_" + str(lineNo) +".tif"
	fileNull = outWorkspace+"\\SLM_LFP_Null_" + str(lineNo) +".tif"
	fileFootprint = outWorkspace +"\\SLM_LFP_Footprint_" + str(lineNo) +".shp"
	
	# Load segment list
	segment_list = []
	rows = arcpy.SearchCursor(fileSeg)
	shapeField = arcpy.Describe(fileSeg).ShapeFieldName
	for row in rows:
		feat = row.getValue(shapeField)   #creates a geometry object
		Corridor_Threshold = float(row.getValue(Corridor_Threshold_Field))
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
	RasterCorridor = ( (RasterCorridor-CorrMin) > Corridor_Threshold)
	RasterCorridor.save(fileCorridorMin)
	
	# Process: Stamp CC and Max Line Width
	RasterClass = SetNull(IsNull(Raster(fileCorridorMin)),(Raster(fileCorridorMin)+(Raster(Canopy_Raster)>=1))>0)
	RasterClass.save(fileThreshold)
	del RasterCorridor, RasterClass
	
	# Process: Expand
	arcpy.gp.Expand_sa(fileThreshold, fileExpand, Expand_And_Shrink_Cell_Range, "1")

	# Process: Shrink
	arcpy.gp.Shrink_sa(fileExpand, fileShrink, Expand_And_Shrink_Cell_Range, "1")
	
	# Process: Boundary Clean
	arcpy.gp.BoundaryClean_sa(fileShrink, fileClean, "NO_SORT", "TWO_WAY")
	
	# Process: Set Null
	arcpy.gp.SetNull_sa(fileClean, "1", fileNull, "VALUE > 0")
	
	# Process: Raster to Polygon
	arcpy.RasterToPolygon_conversion(fileNull, fileFootprint, "SIMPLIFY", "VALUE", "SINGLE_OUTER_PART", "")
	
	#Clean temporary files
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

def HasField(fc, fi):
  fieldnames = [field.name for field in arcpy.ListFields(fc)]
  if fi in fieldnames:
    return True
  else:
    return False
	
def main():
	global outWorkspace
	outWorkspace = slmc.SetupWorkspace(workspaceName)

	if(HasField(Centerline_Feature_Class, Corridor_Threshold_Field) == False):
		slmc.log("ERROR: There is no field named "+Corridor_Threshold_Field+" in the input lines")
		return False

	# Prepare input lines for multiprocessing
	numLines = slmc.SplitLines(Centerline_Feature_Class, outWorkspace, "LFP", ProcessSegments, Corridor_Threshold_Field)
	
	pool = multiprocessing.Pool(processes=slmc.GetCores())
	slmc.log("Multiprocessing line corridors...")
	pool.map(workLines, range(1,numLines+1))
	pool.close()
	pool.join()
	slmc.logStep("Corridor multiprocessing")
	
	slmc.log("Merging footprint layers...")
	tempShapefiles = arcpy.ListFeatureClasses()
	fileMerge = outWorkspace +"\\SLM_LFP_Merge.shp"
	arcpy.Merge_management(tempShapefiles,fileMerge)
	arcpy.Dissolve_management(fileMerge,Output_Footprint)
	for shp in tempShapefiles:
		arcpy.Delete_management(shp)
	arcpy.Delete_management(fileMerge)
	slmc.logStep("Merging")
	
if __name__ == '__main__':
	try:
		main()
	except Exception as e: 
		print(e)
	input("<Press any key to exit>")