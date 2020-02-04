# ---------------------------------------------------------------------------
#
# SLM_SplitByPolygon.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: Splits the input lines where they intersect the edges of the input
# polygons
#
# ---------------------------------------------------------------------------

import arcpy
from . import SLM_Common as slmc

def main():
	# Setup script path and workspace folder
	outWorkspace = slmc.SetupWorkspace("SLM_SBP_output")
	arcpy.env.workspace = outWorkspace
	arcpy.env.overwriteOutput = True
	
	# Load arguments from file
	args = slmc.GetArgs("SLM_SBP_params.txt")
	
	# Tool arguments
	Input_Features = args[0].rstrip()
	Clip_Features = args[1].rstrip()
	Out_Features = args[2].rstrip()

	# Local variables:
	OutClip = outWorkspace+"\\SLM_SBP_OutClip.shp"
	OutErase = outWorkspace+"\\SLM_SBP_OutErase.shp"
	OutMerge = outWorkspace+"\\SLM_SBP_OutMerge.shp"
	
	# Process: Clip
	arcpy.Clip_analysis(Input_Features, Clip_Features, OutClip, "")

	# Process: Erase
	arcpy.Erase_analysis(Input_Features, Clip_Features, OutErase, "")

	# Process: Merge
	arcpy.Merge_management([OutClip,OutErase], OutMerge, "")

	# Process: Multipart To Singlepart
	arcpy.MultipartToSinglepart_management(OutMerge, Out_Features)