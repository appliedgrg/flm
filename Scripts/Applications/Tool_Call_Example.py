# System imports
import os
import sys

# ArcGIS imports
try:
    import arcpy
    arcpy.CheckOutExtension("Spatial")

    if arcpy.CheckProduct("ArcInfo") == "Available":
        msg = 'ArcGIS Advanced license is available'
        print(msg)
    else:
        msg = 'ArcGIS Advanced license not available'
        print(msg)
        sys.exit(msg)

except Exception as e:
    print("Tool Call Example arcpy check.")
    print(e)

# Add Scripts folder to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Local imports
import FLM_Tools

def main():
    """ This is an example script for calling FLM tools for processing single dataset"""

    # Add Scripts folder to sys.path
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    # Set arcpy environment variables
    arcpy.env.overwriteOutput = True

    # Coordinate Reference System: NAD 1983 10TM AEP Forest
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3400)

    # Check out the ArcGIS Spatial Analyst extension license
    arcpy.CheckOutExtension("Spatial")

    # process footprint
    baseDir = r"C:\FLM\Region_3\Block_2\Cell_42"
    in_chm = os.path.join(baseDir, r"Original\3_2_42_raster.tif")
    in_line = os.path.join(baseDir, r"Edited\3_2_42_input_line_confirmed.shp")
    in_canopy_raster = os.path.join(baseDir, r"Original\3_2_42_output_canopy.tif")
    in_cost_raster = os.path.join(baseDir, r"Original\3_2_42_output_canopy.tif")
    out_center_line = os.path.join(baseDir, r"Edited\3_2_42_output_center_line_confirmed-new.shp")
    in_line_ft = out_center_line
    out_footprint = os.path.join(baseDir, r"Edited\3_2_42_footprint.shp")
    out_attribute_whole = os.path.join(baseDir, r"Line_Attributes\temp_whole.shp")

    FLM_Tools.centerline(in_line, in_cost_raster, out_center_line)
    # FLM_Tools.lineFootprint(in_line_ft, in_canopy_raster, in_cost_raster, out_footprint)
    # FLM_Tools.lineAttribute("WHOLE_LINE", out_center_line, out_footprint, in_chm, out_attribute_whole)


if __name__ == "__main__":
    main()