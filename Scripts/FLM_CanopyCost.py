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
# FLM_CanopyCost.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Creates a canopy raster and a cost raster from a CHM input raster.
# The output rasters are used for subsequent FLM tools.
#
# ---------------------------------------------------------------------------

# Import arcpy module
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc


def main(argv=None):
	# Setup script path and output folder
	outWorkspace = flmc.SetupWorkspace("FLM_CC_output")
	arcpy.env.workspace = outWorkspace
	arcpy.env.scratchWorkspace = outWorkspace
	arcpy.env.overwriteOutput = True
	
	# Load arguments from file
	if argv:
		args = argv
	else:
		args = flmc.GetArgs("FLM_CC_params.txt")

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
	FLM_CC_EucRaster = outWorkspace+"\\FLM_CC_EucRaster.tif"
	FLM_CC_SmoothRaster = outWorkspace+"\\FLM_CC_SmoothRaster.tif"
	FLM_CC_Mean = outWorkspace+"\\FLM_CC_Mean.tif"
	FLM_CC_StDev = outWorkspace+"\\FLM_CC_StDev.tif"
	FLM_CC_CostRaster = outWorkspace+"\\FLM_CC_CostRaster.tif"

	# Process: Turn CHM into a Canopy Closure (CC) map
	flmc.log("Applying height threshold to CHM...")
	arcpy.gp.Con_sa(CHM_Raster, 1, Output_Canopy_Raster, 0, "VALUE > "+str(Min_Canopy_Height))
	flmc.logStep("Height threshold")
	
	# Process: CC Mean
	flmc.log("Calculating Focal Mean...")
	arcpy.gp.FocalStatistics_sa(Output_Canopy_Raster, FLM_CC_Mean, Tree_Search_Area, "MEAN")
	flmc.logStep("Focal Mean")
	
	# Process: CC StDev
	flmc.log("Calculating Focal StDev..")
	arcpy.gp.FocalStatistics_sa(Output_Canopy_Raster, FLM_CC_StDev, Tree_Search_Area, "STD")
	flmc.logStep("Focal StDev")
	
	# Process: Euclidean Distance
	flmc.log("Calculating Euclidean Distance From Canopy...")
	EucAllocation(Con(arcpy.Raster(Output_Canopy_Raster) >= 1, 1, ""), "", "", "", "", FLM_CC_EucRaster, "")
	smoothCost = (float(Max_Line_Distance) - arcpy.Raster(FLM_CC_EucRaster))
	smoothCost = Con(smoothCost > 0, smoothCost, 0)/float(Max_Line_Distance)
	smoothCost.save(FLM_CC_SmoothRaster)
	flmc.logStep("Euclidean Distance")
	
	# Process: Euclidean Distance
	flmc.log("Calculating Cost Raster...")
	arcpy.env.compression = "NONE"
	Raster_CC = arcpy.Raster(Output_Canopy_Raster)
	Raster_Mean = arcpy.Raster(FLM_CC_Mean)
	Raster_StDev = arcpy.Raster(FLM_CC_StDev)
	Raster_Smooth = arcpy.Raster(FLM_CC_SmoothRaster)
	avoidance = max(min(float(CanopyAvoidance), 1), 0)

	# TODO: shorten following sentence
	outRas = Power(Exp(Con((Raster_CC == 1), 1, Con((Raster_Mean+Raster_StDev <= 0), 0, (1+(Raster_Mean-Raster_StDev)/(Raster_Mean+Raster_StDev))/2)*(1-avoidance) + Raster_Smooth*avoidance)), float(Cost_Raster_Exponent))
	outRas.save(FLM_CC_CostRaster)
	flmc.logStep("Cost Raster")
	
	flmc.log("Saving Outputs...")
	arcpy.CopyRaster_management(outRas, Output_Cost_Raster, "DEFAULTS")
	arcpy.ClearWorkspaceCache_management()
