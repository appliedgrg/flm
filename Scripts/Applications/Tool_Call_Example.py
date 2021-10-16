# System imports
import os
import sys

# ArcGIS imports
import arcpy

# Local imports
# Add Scripts folder to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import FLM_Tools


def main():
    """ This is an example script for calling FLM tools for processing single dataset"""

    # Set arcpy environment variables
    arcpy.env.overwriteOutput = True

    # Coordinate Reference System: NAD 1983 10TM AEP Forest
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3400)

    # Check out the ArcGIS Spatial Analyst extension license
    arcpy.CheckOutExtension("Spatial")

    # process footprint
    # baseDir = r"C:\FLM\Line_Editing_Staging\Region_3\Block_2\Cell_42"
    # in_chm = os.path.join(baseDir, r"Original\3_2_42_raster.tif")
    # in_line = os.path.join(baseDir, r"Edited\3_2_42_input_line_confirmed.shp")
    # in_canopy_raster = os.path.join(baseDir, r"Original\3_2_42_output_canopy.tif")
    # in_cost_raster = os.path.join(baseDir, r"Original\3_2_42_output_cost.tif")
    # out_center_line = os.path.join(baseDir, r"Edited\3_2_42_output_center_line_confirmed-new.shp")
    # in_line_ft = out_center_line
    # out_footprint = os.path.join(baseDir, r"Edited\3_2_42_footprint.shp")
    # out_attribute_whole = os.path.join(baseDir, r"Line_Attributes\temp_whole.shp")

    baseDir = r"D:\Temp\PreTagging"
    in_chm = os.path.join(baseDir, r"Tag_CHM.tif")
    in_line = os.path.join(baseDir, r"Tag_Line_edited.shp")
    in_canopy_raster = os.path.join(baseDir, r"Tag_Canopy.tif")
    in_cost_raster = os.path.join(baseDir, r"Tag_Cost.tif")
    out_center_line = os.path.join(baseDir, r"Tag_Line_output.shp")
    out_footprint = os.path.join(baseDir, r"Tag_footprint.shp")
    out_attribute_whole = os.path.join(baseDir, r"temp_whole.shp")  # WHOLE-LINE
    out_attribute_arbitrary = os.path.join(baseDir, r"temp_arbitrary.shp")  # ARBITRARY
    out_attribute_in_features = os.path.join(baseDir, r"temp_in_features.shp")  # IN-FEATURES
    out_attribute_line_crossings = os.path.join(baseDir, r"temp_line_crossings.shp")  # LINE-CROSSINGS

    # FLM_Tools.centerline(in_line, in_cost_raster, out_center_line)
    # FLM_Tools.lineFootprint(in_line, in_canopy_raster, in_cost_raster, out_footprint)
    FLM_Tools.lineAttribute("LINE-CROSSINGS", out_center_line, out_footprint, in_chm, out_attribute_line_crossings)


if __name__ == "__main__":
    main()
