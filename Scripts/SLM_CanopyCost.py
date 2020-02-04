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
# SLM_CanopyCost.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: Creates a canopy raster and a cost raster from a CHM input raster.
# The output rasters are used for subsequent SLM tools.
#
# ---------------------------------------------------------------------------

# Import arcpy module
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
from . import SLM_Common as slmc

def main():
	# Setup script path and output folder
	outWorkspace = slmc.SetupWorkspace("SLM_CC_output")
	arcpy.env.workspace = outWorkspace
	arcpy.env.overwriteOutput = True
	
	# Load arguments from file
	args = slmc.GetArgs("SLM_CC_params.txt")

	# Tool arguments
	CHM_Raster = args[0].rstrip()
	Min_Canopy_Height = float(args[1].rstrip())
	Tree_Search_Area = "Circle "+str(float(args[2].rstrip()))+" MAP"
	Max_Line_Distance = float(args[3].rstrip())
	CanopyAvoidance = float(args[4].rstrip())
	Cost_Raster_Exponent = float(args[5].rstrip())
	Output_Canopy_Raster = args[6].rstrip()
	Output_Cost_Raster = args[7].rstrip()

	# Local variables:
	SLM_CC_EucRaster = outWorkspace+"\\SLM_CC_EucRaster.tif"
	SLM_CC_SmoothRaster = outWorkspace+"\\SLM_CC_SmoothRaster.tif"
	SLM_CC_Mean = outWorkspace+"\\SLM_CC_Mean.tif"
	SLM_CC_StDev = outWorkspace+"\\SLM_CC_StDev.tif"
	SLM_CC_CostRaster = outWorkspace+"\\SLM_CC_CostRaster.tif"

	# Process: Turn CHM into a Canopy Closure (CC) map
	slmc.log("Applying height threshold to CHM...")
	arcpy.gp.Con_sa(CHM_Raster, 1, Output_Canopy_Raster, 0, "VALUE > "+str(Min_Canopy_Height))
	slmc.logStep("Height threshold")
	
	# Process: CC Mean
	slmc.log("Calculating Focal Mean...")
	arcpy.gp.FocalStatistics_sa(Output_Canopy_Raster, SLM_CC_Mean, Tree_Search_Area, "MEAN")
	slmc.logStep("Focal Mean")
	
	# Process: CC StDev
	slmc.log("Calculating Focal StDev..")
	arcpy.gp.FocalStatistics_sa(Output_Canopy_Raster, SLM_CC_StDev, Tree_Search_Area, "STD")
	slmc.logStep("Focal StDev")
	
	# Process: Euclidean Distance
	slmc.log("Calculating Euclidean Distance From Canopy...")
	EucAllocation(Con(arcpy.Raster(Output_Canopy_Raster)>=1,1,""),"","","","",SLM_CC_EucRaster,"")
	smoothCost = (float(Max_Line_Distance) - arcpy.Raster(SLM_CC_EucRaster))
	smoothCost = Con(smoothCost>0,smoothCost,0)/float(Max_Line_Distance)
	smoothCost.save(SLM_CC_SmoothRaster)
	slmc.logStep("Euclidean Distance")
	
	# Process: Euclidean Distance
	slmc.log("Calculating Cost Raster...")
	arcpy.env.compression = "NONE"
	Raster_CC = arcpy.Raster(Output_Canopy_Raster)
	Raster_Mean = arcpy.Raster(SLM_CC_Mean)
	Raster_StDev = arcpy.Raster(SLM_CC_StDev)
	Raster_Smooth = arcpy.Raster(SLM_CC_SmoothRaster)
	avoidance = max(min(float(CanopyAvoidance),1),0)
	outRas = Power(Exp(Con((Raster_CC == 1), 1, Con((Raster_Mean+Raster_StDev<=0),0,(1+(Raster_Mean-Raster_StDev)/(Raster_Mean+Raster_StDev))/2)*(1-avoidance) + Raster_Smooth*avoidance )),float(Cost_Raster_Exponent))
	outRas.save(SLM_CC_CostRaster)
	slmc.logStep("Cost Raster")
	
	slmc.log("Saving Outputs...")
	arcpy.CopyRaster_management(outRas,Output_Cost_Raster,"DEFAULTS")
