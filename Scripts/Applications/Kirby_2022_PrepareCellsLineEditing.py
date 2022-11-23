
import os
import sys
import inspect

import datetime
import arcpy
from arcpy.sa import *
from arcpy.da import *

from shutil import copyfile

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

def PrepareCell(basePath, cellFile, allLineFile):
    """ This function will traverse all cells and clip lines by shrinked cell footprint
        basePath:
        cellFile: cell file
        allLineFile: Shapefile with all lines
    """
    fields_cell = ["Shape@", "site"]
    try:
        cells = arcpy.da.SearchCursor(cellFile, fields_cell)
    except Exception as err:
        print(err)

    for cell in cells:
        cellLinePath = os.path.join(basePath, 'Site'+cell[1], 'Lines')
        cellLineFile = os.path.join(cellLinePath, 'seedpoints_Site' + cell[1] + '.shp')
        print("Start processing cell {}".format(cellLineFile))

        # clip line to cell extent
        if not arcpy.Exists(cellLineFile):
            arcpy.Clip_analysis(allLineFile, cell[0].buffer(-30), cellLineFile)

        print("Cell {} processed".format(cellLineFile))


def main():

    """ This is the main function"""

    # Set arcpy environment variables
    arcpy.env.overwriteOutput = True

    # Coordinate Reference System
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2956)

    # Check out the ArcGIS Spatial Analyst extension license
    arcpy.CheckOutExtension("Spatial")

    # Line Footprint Checkups:
    global basePath
    basePath = r'D:\Line_Editing\Kirby_2022'
    cellFile = basePath + r'\Rasters_Footprints\site_footprints.shp'
    lineFile = basePath + r'\All_Lines\All_Lines_EPSG_2956_Cleaned.shp'

    PrepareCell(basePath, cellFile, lineFile)


if __name__ == "__main__":
    main()
