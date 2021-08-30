# System imports
import os
import sys

# ArcGIS imports
import arcpy

# Add Scripts folder to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Local imports
import FLM_Tools

def main():

    """ Prepare input seismic lines and raster for each cell"""

    # Add Scripts folder to sys.path
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    # Set arcpy environment variables
    arcpy.env.overwriteOutput = True

    # Coordinate Reference System: NAD 1983 10TM AEP Forest
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3714)

    # Execute MakeNetCDFRasterLayer
    # Check out the ArcGIS Spatial Analyst extension license
    arcpy.CheckOutExtension("Spatial")

    # traverse all the rows to prepare for extracting
    spatialReference = arcpy.SpatialReference(3714)

    # process footprint
    baseDir = r"C:\Temp\Multi_Intersection_Streams_withSDM_NoFilledDEM"
    in_line = os.path.join(baseDir, r"HC_MC_Multi_Intersection_Stream.shp")
    in_line_footprint = os.path.join(baseDir, r"CenterlineOutput\FLMcenterline_output.shp")
    in_canopy_raster = os.path.join(baseDir, r"Clip_CanopyRaster.tif")
    in_cost_raster = os.path.join(baseDir, r"Clip_CostRaster.tif")
    out_center_line = os.path.join(baseDir, r"CenterlineOutput\output_centerline.shp")
    outFootprint = os.path.join(baseDir, r"Footprint\out_footprint.shp")

    # FLM_Tools.centerline(in_line, in_cost_raster, out_center_line)
    FLM_Tools.lineFootprint(in_line_footprint, in_canopy_raster, in_cost_raster, outFootprint)


if __name__ == "__main__":
    main()