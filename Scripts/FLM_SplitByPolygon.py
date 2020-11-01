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
# FLM_SplitByPolygon.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Splits the input lines where they intersect the edges of the input
# polygons
#
# ---------------------------------------------------------------------------

import arcpy
from . import FLM_Common as flmc

def main():
	# Setup script path and workspace folder
	outWorkspace = flmc.SetupWorkspace("FLM_SBP_output")
	arcpy.env.workspace = outWorkspace
	arcpy.env.overwriteOutput = True
	
	# Load arguments from file
	args = flmc.GetArgs("FLM_SBP_params.txt")
	
	# Tool arguments
	Input_Features = args[0].rstrip()
	Clip_Features = args[1].rstrip()
	Out_Features = args[2].rstrip()

	# Local variables:
	OutIdentity = outWorkspace+"\\FLM_SBP_OutIdentity.shp"
	
	# Process: Identity
	arcpy.Identity_analysis(Input_Features, Clip_Features, OutIdentity, join_attributes="ALL", cluster_tolerance="", relationship="NO_RELATIONSHIPS")
	
	# Process: Multipart To Singlepart
	arcpy.MultipartToSinglepart_management(OutIdentity, Out_Features)