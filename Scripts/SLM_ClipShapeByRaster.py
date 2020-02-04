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
# SLM_ClipShapeByRaster.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: Extracts input features that overlay raster cells which are not 
# NoData. This is useful to prepare input seismic lines for corridor analysis,
# since vertices must overlap with valid cells for least cost methods.
#
# ---------------------------------------------------------------------------

import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
from . import SLM_Common as slmc

def main():
	# Setup script path and workspace folder
	outWorkspace = slmc.SetupWorkspace("SLM_CSR_output")
	arcpy.env.workspace = outWorkspace
	arcpy.env.overwriteOutput = True
	
	# Load arguments from file
	args = slmc.GetArgs("SLM_CSR_params.txt")
	
	# Tool arguments
	InShapefile = args[0].rstrip()
	InRaster = args[1].rstrip()
	ShrinkSize = args[2].rstrip()
	OutShapefile = args[3].rstrip()

	# Local variables:
	SLM_CSR_IsNull = outWorkspace+"\\SLM_CSR_IsNull.tif"
	SLM_CSR_SetNull = outWorkspace+"\\SLM_CSR_SetNull.tif"
	SLM_CSR_Shrink = outWorkspace+"\\SLM_CSR_Shrink.tif"
	SLM_CSR_RasterPoly = outWorkspace+"\\SLM_CSR_RasterPoly.shp"
	
	arcpy.gp.IsNull_sa(InRaster, SLM_CSR_IsNull)

	arcpy.gp.SetNull_sa(SLM_CSR_IsNull, "1", SLM_CSR_SetNull, "Value = 1")

	arcpy.gp.Shrink_sa(SLM_CSR_SetNull, SLM_CSR_Shrink, ShrinkSize, "1")

	arcpy.RasterToPolygon_conversion(SLM_CSR_Shrink, SLM_CSR_RasterPoly, simplify="NO_SIMPLIFY", raster_field="Value", create_multipart_features="SINGLE_OUTER_PART", max_vertices_per_feature="")

	arcpy.Clip_analysis(InShapefile, SLM_CSR_RasterPoly, OutShapefile, cluster_tolerance="0 Meters")