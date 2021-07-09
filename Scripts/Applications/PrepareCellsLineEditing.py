import os
import datetime
import arcpy
from arcpy.sa import *
from arcpy.da import *

from shutil import copyfile

import os, sys, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

def PrepareCell(basePath, cellFile, lineFile, CHMFile):
    """ This function will traverse all cells in cellFile, clip seismic lines and CHM rasters
        in cells and generate center lines
        lineFile: seismic line file
        cellFile: cell file
        CHMFile: CHM derived from mosaic dataset
    """
    fields_cell = ["Shape@", "Region", "Block", "Cell"]
    try:
        cells = arcpy.da.SearchCursor(cellFile, fields_cell)
    except Exception as err:
        print(err)

    CHMExtent = arcpy.Raster(CHMFile).extent

    for cell in cells:
        # only process region 3, block 2
        if cell[1] != 3 or cell[2] != 2 or cell[3] not in range(30, 31):
            continue

        cellPath = os.path.join('Region_' + str(cell[1]), 'Block_' + str(cell[2]), 'Cell_' + (str(cell[3]).zfill(2)))
        cellPath = os.path.join(basePath, cellPath)
        os.makedirs(os.path.join(cellPath, 'Original'), exist_ok=True)
        os.makedirs(os.path.join(cellPath, 'Edited'), exist_ok=True)

        cellString = list(map(str, cell[1:4]))
        cellString[2] = cellString[2].zfill(2)
        fileName = '_'.join(cellString)
        # cellBufferNone = os.path.join(cellPath, 'bufferNone.shp')
        # cellBuffer200M = os.path.join(cellPath, 'buffer200M.shp')
        cellLineFile = os.path.join(cellPath, 'Original', fileName+'_input_line.shp')
        cellRasterFile = os.path.join(cellPath, 'Original', fileName+'_raster.tif')

        print("Start processing cell {}".format(fileName))

        # clip line to cell extent
        if not arcpy.Exists(cellLineFile):
            #arcpy.Copy_management(cell[0], cellBufferNone)
            arcpy.Clip_analysis(lineFile, cell[0], cellLineFile)

        # Clip CHM raster to buffered cell extent
        # Only do this when cell intersect CHM raster
        if not cell[0].disjoint(CHMExtent):
            if not arcpy.Exists(cellRasterFile):
                #arcpy.Buffer_analysis(cell[0], cellBuffer200M, "200 meters")
                arcpy.Clip_management(CHMFile, "#", cellRasterFile, cell[0].buffer(200), "#", "ClippingGeometry")
        else:
            print("Cell {} has no intersection with CHM raster".format(fileName))

        print("Cell {} processed".format(fileName))


def main():

    """ This is the main function"""

    # Set arcpy environment variables
    arcpy.env.overwriteOutput = True

    # Coordinate Reference System: NAD 1983 10TM AEP Forest
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3400)

    # Execute MakeNetCDFRasterLayer
    # Check out the ArcGIS Spatial Analyst extension license
    arcpy.CheckOutExtension("Spatial")

    # traverse all the rows to prepare for extracting
    spatialReference = arcpy.SpatialReference(3400)

    # Line Footprint Checkups:
    global basePath
    basePath = r'E:\Line_Editing_Staging'
    cellFile = r'X:\Plan\Plan_Cells\Plan_Cell_8x8.shp'
    lineFile = (r'X:\Plan\o20_SeismicLines_Centerlines_HFI2018_in_BERA_Study_Area'
                r'\o20_SeismicLines_Centerlines_HFI2018_in_BERA_Study_Area.shp')
    CHMFile = r'E:\Line_Editing_Staging\Rasters\CHM_3_2.tif'
    # Mosaic datasets
    #fullFeature = r'X:\Temporary_Project\Temporary_Project.gdb\Full_Feature'
    #bareEarth = r'X:\Temporary_Project\Temporary_Project.gdb\Bare_Earth'
    #CHM = arcpy.Raster(CHMFile)

    #CHM = 'X:\Temporary_Project\Temporary_Project.gdb\cold_lake_CHM'
    CHM = 'X:\Temporary_Project\Temporary_Project.gdb\GOA_Mosaic_3_2'
    #CHM = 'X:\OGL\LiDEA_II_CHM.tif'

    PrepareCell(basePath, cellFile, lineFile, CHM)


if __name__ == "__main__":
    main()
