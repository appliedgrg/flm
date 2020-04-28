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
# SLM_RasterLineAttributes.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: Samples a raster image along lines and assigns cell statistics to 
# each line
#
# ---------------------------------------------------------------------------

# Import arcpy module
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
from . import SLM_Common as slmc
from . import SLM_Attribute_Functions as slma

def main():
	# Setup script path and output folder
	outWorkspace = slmc.SetupWorkspace("SLM_RLA_output")
	arcpy.env.workspace = outWorkspace
	arcpy.env.overwriteOutput = True
	
	# Load arguments from file
	args = slmc.GetArgs("SLM_RLA_params.txt")
			
	# Tool arguments
	Input_Lines = args[0].rstrip()
	Input_Raster = args[1].rstrip()
	SamplingType = args[2].rstrip()
	Measure_Interval = float(args[3].rstrip())
	Segment_Length = float(args[4].rstrip())
	Tolerance_Radius = float(args[5].rstrip())
	Sampling_Method = args[6].rstrip()
	Attributed_Segments = args[7].rstrip()

	# Local variables:
	SLM_RLA_Measure_Points = outWorkspace+"\\SLM_RLA_Measure_Points.shp"
	SLM_RLA_Attributed_Points = outWorkspace+"\\SLM_RLA_Attributed_Points.shp"

	slmc.log("Generating sample points along lines...")
	arcpy.GeneratePointsAlongLines_management(Input_Lines, SLM_RLA_Measure_Points, "DISTANCE", Measure_Interval, "", "")
	slmc.logStep("Spawning sample points")

	slmc.log("Extracting raster values at sample points...")
	arcpy.gp.ExtractValuesToPoints_sa(SLM_RLA_Measure_Points, Input_Raster, SLM_RLA_Attributed_Points)
	slmc.logStep("Raster sampling")

	# Find RASTERVALU field and set user defined sampling (merge) method
	fieldmappings = arcpy.FieldMappings()
	fieldmappings.addTable(SLM_RLA_Attributed_Points)
	RastervaluIndex = fieldmappings.findFieldMapIndex("RASTERVALU")
	fieldmap = fieldmappings.getFieldMap(RastervaluIndex)
	fieldmap.mergeRule = Sampling_Method #Set sampling method (Mean, Minimum, Maximum, Standard Deviation, Etc..)
	fieldmappings = arcpy.FieldMappings()
	fieldmappings.addFieldMap (fieldmap)

	slmc.log("Splitting lines...")
	SLM_RLA_Segmented_Lines = slma.SlmLineSplit(outWorkspace,Input_Lines,SamplingType,Segment_Length,Tolerance_Radius)
	slmc.logStep("Line split")

	slmc.log("Generating raster statistics along line segments")
	arcpy.SpatialJoin_analysis(SLM_RLA_Segmented_Lines, SLM_RLA_Attributed_Points, Attributed_Segments, "JOIN_ONE_TO_ONE", "KEEP_COMMON", fieldmappings, "INTERSECT", Tolerance_Radius, "")
