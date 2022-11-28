# System imports
import inspect
import os
import sys
from shutil import copyfile

# ArcGIS imports
import arcpy
from arcpy.da import *
from arcpy.sa import *

# Local imports
# Add Scripts folder to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import FLM_Tools


def setLayerStyle(layer, lineColor, lineWidth, fillColor=None):
    """Set layer style for aprx project"""

    cim_lyr = layer.getDefinition('V2')

    # Modify the color, width and dash template for the SolidStroke layer
    symLvl1 = cim_lyr.renderer.symbol.symbol.symbolLayers[0]
    symLvl1.color.values = lineColor
    symLvl1.width = lineWidth
    #ef1 = symLvl1.effects[0]  # Note, deeper indentation
    #ef1.dashTemplate = [20, 30]  # Only works if there is an existing dash template

    # Modify the color/transparency for the SolidFill layer
    if fillColor:
        symLvl2 = cim_lyr.renderer.symbol.symbol.symbolLayers[1]
        symLvl2.color.values = fillColor

    # Push the changes back to the layer object
    layer.setDefinition(cim_lyr)


def PrepareArcGISproProject(cellPath, fileName):
    """Prepare aprx project for Potoplot quality check
       An group layer will be created for each photo plot
       CHM, flm produced layers: center line, line footprint and rasters will be added to the group"""

    from distutils.dir_util import copy_tree
    copy_tree(r'Y:\Cell_Project', os.path.join(cellPath, r'Cell_Project'))

    aprx = arcpy.mp.ArcGISProject(os.path.join(cellPath, os.path.join(r'Cell_Project', 'Cell_Project.aprx')))

    # Add all layers from photoplot folder
    map = aprx.listMaps()[0]  # map in aprx project
    refLayer = map.listLayers()[0]

    layer = map.addDataFromPath(input_line)
    lineColor = [76, 230, 0, 100]
    lineWidth = 2
    setLayerStyle(layer, lineColor, lineWidth)
    map.insertLayer(refLayer, layer)
    map.removeLayer(layer)

    layer = map.addDataFromPath(output_center_line)
    lineColor = [0, 112, 255, 100]
    lineWidth = 2
    setLayerStyle(layer, lineColor, lineWidth)
    map.insertLayer(refLayer, layer)
    map.removeLayer(layer)

    layer = map.addDataFromPath(input_raster)
    map.insertLayer(refLayer, layer)
    map.removeLayer(layer)

    # Save project
    aprx.save()


def ProcessCell(cellFolder, siteLetter, paramsList, lineType):
    """ Process single cell
        cellFolder:
        siteLetter:
        paramsList:
        lineType:
    """

    # Prepare parameters
    global paramCCHtThresh
    global paramCCSearchRadius
    global paramCCLineDist
    global paramCCAvoidance
    global paramCCExponent
    global paramCLRadius
    global paramLFLineWidth
    global paramSegments

    params = paramsList[lineType]
    paramCCHtThresh = params[0]
    paramCCSearchRadius = params[1]
    paramCCLineDist = params[2]
    paramCCAvoidance = params[3]
    paramCCExponent = params[4]
    paramCLRadius = params[5]
    paramLFLineWidth = params[6]
    paramSegments = params[7]

    cellPathCHM = os.path.join(basePath, cellFolder, 'CHM')
    cellPathLines = os.path.join(basePath, cellFolder, 'Lines')

    input_raster = os.path.join(cellPathCHM, 'CHM_Kirby_Site' + siteLetter + r'.tif')
    input_line = os.path.join(cellPathLines, 'seedpoints_Site' + siteLetter + r'.shp')

    # Verify if the input line exist
    if not arcpy.Exists(input_raster) or not arcpy.Exists(input_line):
        print("Input file(s) not exist.")
        return

    seismic = {"conventional": "CONVENTIONAL-SEISMIC", "low_impact": "LOWIMPACT-SEISMIC", "trail": "TRAIL"}
    if lineType != "default":
        input_line_temp = fileName + "_input_line_" + lineType + ".shp"
        query = "FEATURE_TY={}".format(seismic[linetype])
        arcpy.FeatureClassToFeatureClass_conversion(input_line, cellPathOriginal, input_line_temp, query)
        input_line = os.path.join(cellPathOriginal, input_line_temp)

    extension = ""
    if lineType != "default":
        extension = "_" + lineType

    output_canopy_raster = os.path.join(cellPathCHM, 'Canopy_Site' + siteLetter + r'.tif')
    output_cost_raster = os.path.join(cellPathCHM, 'Cost_Site' + siteLetter + r'.tif')
    output_center_line = os.path.join(cellPathLines, 'Centerline_Site' + siteLetter + r'.shp')
    output_line_footprint = os.path.join(cellPathLines, 'Footprint_Site' + siteLetter + r'.shp')
    output_line_footprint_dyn = os.path.join(cellPathLines, 'Footprint_Site' + siteLetter + r'_dyn.shp')

    # Verify if the input line exist
    if not arcpy.Exists(input_raster) or not arcpy.Exists(input_line):
        print("Input raster file(s) not exist.")
        return

    # Generate cost raster
    print("Cell {} canopy cost tool started.".format(input_raster))
    FLM_Tools.canopyCost(input_raster, output_canopy_raster, output_cost_raster)
    print("Cell {} canopy cost tool finished.".format(input_raster))

    # Generate center line
    print("Cell {} centerline tool started.".format(input_line))
    FLM_Tools.centerline(input_line, output_cost_raster, output_center_line)
    print("Cell {} centerline tool finished.".format(input_line))

    # Generate footprint
    print("Cell {} footprint tool started.".format(output_line_footprint))
    FLM_Tools.lineFootprint(output_center_line, output_canopy_raster, output_cost_raster, output_line_footprint)
    print("Cell {} footprint tool finished.".format(output_line_footprint))

    # Generate dynamic footprint
    print("Cell {} dynamic footprint tool started.".format(output_line_footprint_dyn))
    FLM_Tools.dynamicLineFootprint(output_center_line, input_raster, output_line_footprint_dyn)
    print("Cell {} dynamic footprint tool finished.".format(output_line_footprint_dyn))

    return output_center_line


def ProcessCells(cells, paramsList, basePath, discriminateLineType=False):
    """ This function will traverse all cells
    """
    for cell in cells:
        cellFolder = os.path.join("Site" + str(cell))
        cellPath = os.path.join(basePath, cellFolder)
        fileName = str(cell)

        if discriminateLineType:
            outputLineFiles = []
            for lineType in ("conventional", "low_impact", "trail"):
                fileTemp = ProcessCell(cellPath, fileName, paramsList[lineType], lineType)
                outputLineFiles.append(fileTemp)
                # Merge three types of output line
                outputCenterLine = os.path.join(cellPath, fileName + "_output_centerline.shp")
                arcpy.Merge_management(outputLineFiles, outputCenterLine)
        else:
            ProcessCell(cellPath, cell, paramsList, "default")

            # Prepare ArcGIS Pro project
            # PrepareArcGISproProject(cellPath, fileName)

        print("Cell {} processed".format(str(cell)))


def main():
    """ Prepare input seismic lines and raster for each cell"""
    # Set arcpy environment variables
    arcpy.env.overwriteOutput = True

    # Coordinate Reference System
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2956)

    # Check out the ArcGIS Spatial Analyst extension license
    arcpy.CheckOutExtension("Spatial")

    # Line Footprint Checkups:
    global basePath
    basePath = r'D:\Line_Editing\Kirby_2022'

    cells = [x for x in ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L')]
    paramsList = {"conventional": ("2", "3", "10", "0.3", "1.5", "30", "32", "True", r""),
                  "low_impact": ("2", "3", "10", "0.3", "1.5", "30", "32", "True", r""),
                  "trail": ("2", "3", "10", "0.3", "1.5", "30", "32", "True", r""),
                  "default": ("0.5", "1.5", "1.5", "0.0", "1", "15", "32", "True", r"")}

    discriminateLineType = False
    ProcessCells(cells, paramsList, basePath, discriminateLineType)


if __name__ == "__main__":
    main()
