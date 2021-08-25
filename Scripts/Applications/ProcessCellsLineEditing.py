# System imports
import inspect
import os
import sys
from shutil import copyfile

# ArcGIS imports
import arcpy
from arcpy.da import *
from arcpy.sa import *

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

# Local imports


# backup all output_center_line
def BackupOutputCenterLine():

    dirs = next(os.walk(photoplotPath))[1]
    for id in dirs:
        photoplot = photoplotPath + "\\" + id

        if not os.path.exists(photoplot + "\\backups"):
            os.mkdir(photoplot + "\\backups")
        for item in os.listdir(photoplot):
            substr = "output_center_line_" + id
            if substr in item:
                src = photoplot + "\\" + item
                dst = photoplot + "\\backups\\" + item
                copyfile(src, dst)
                print("Backing up file: from {src} to {dst}".format(src=src, dst=dst))


# recover deleted shapefiles
def RecoverOutputCenterLineShapefile(id):
    for item in os.listdir(photoplotPath + "\\" + id + "\\backups"):
        src = photoplotPath + "\\" + id + "\\backups\\" + item
        dst = photoplotPath + "\\" + id + "\\" + item
        copyfile(src, dst)


# Generate cost raster
def CanopyCost():
    import FLM_CanopyCost

    print("Calculating number canopy cost: ", output_canopy_raster)
    argv = [None]*8
    argv[0] = input_raster           # CHM raster
    argv[1] = paramCCHtThresh       # Canopy Height Threshold
    argv[2] = paramCCSearchRadius    # Tree Search Radius
    argv[3] = paramCCLineDist        # Maximum Line Distance
    argv[4] = paramCCAvoidance       # Canopy Avoidance
    argv[5] = paramCCExponent        # Cost Raster Exponent
    argv[6] = output_canopy_raster   # Output Canopy Raster
    argv[7] = output_cost_raster     # Output Cost Raster
    print(argv[6])

    if not os.path.exists(argv[6]) and not os.path.exists(argv[7]):
        FLM_CanopyCost.main(argv)


# Generate centerline
def CenterLine():
    import FLM_CenterLine

    print("Calculating number center line: ", output_center_line)
    argv = [None] * 5
    argv[0] = input_line          # input line
    argv[1] = output_cost_raster  # Cost raster
    argv[2] = paramCLRadius       # line process radius
    argv[3] = paramSegments       # Process segments
    argv[4] = output_center_line  # Output center line

    if not os.path.exists(argv[4]):
        FLM_CenterLine.main(argv)


# Generate line footprint
def LineFootprint():
    import FLM_LineFootprint

    print("Calculating number canopy line footprint: ", output_line_footprint)
    argv = [None] * 8
    argv[0] = output_center_line     # center line
    argv[1] = output_canopy_raster   # canopy raster
    argv[2] = output_cost_raster     # Cost raster
    argv[3] = "CorridorTh"           # corridor threshold field
    argv[4] = paramLFLineWidth       # maximam line width
    argv[5] = str(0)                 # expand and shrink cell range
    argv[6] = paramSegments          # process segments
    argv[7] = output_line_footprint  # Output line foot print

    if os.path.exists(output_center_line) and not os.path.exists(argv[7]):
        FLM_LineFootprint.main(argv)

# Set layer style for aprx project
def setLayerStyle(layer, lineColor, lineWidth, fillColor=None):
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

# Prepare aprx project for Potoplot quality check
# An group layer will be created for each photo plot
# CHM, flm produced layers: center line, line footprint and rasters will be added to the group
def PrepareArcGISproProject(cellPath, fileName):
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


def ProcessCell(cellFolder, fileName, paramsList, lineType):
    """ Process single cell
        cellFolder:
        fileName:
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

    cellPathOriginal = os.path.join(basePath, cellFolder, "Original")
    cellPathEdited = os.path.join(basePath, cellFolder, "Edited")

    global input_raster
    input_raster = os.path.join(cellPathOriginal, fileName+"_raster.tif")
    global input_line
    input_line = os.path.join(cellPathEdited, fileName + "_input_line_confirmed.shp")
    seismic = {"conventional": "CONVENTIONAL-SEISMIC", "low_impact": "LOWIMPACT-SEISMIC", "trail": "TRAIL"}
    if lineType != "default":
        input_line_temp = fileName + "_input_line_" + lineType + ".shp"
        query = "FEATURE_TY={}".format(seismic[linetype])
        arcpy.FeatureClassToFeatureClass_conversion(input_line, cellPathOriginal, input_line_temp, query)
        input_line = os.path.join(cellPathOriginal, input_line_temp)

    extension = ""
    if lineType != "default":
        extension = "_" + lineType

    global output_canopy_raster
    output_canopy_raster = os.path.join(cellPathOriginal, fileName+"_output_canopy"+extension+".tif")
    global output_cost_raster
    output_cost_raster = os.path.join(cellPathOriginal, fileName+"_output_cost"+extension+".tif")
    global output_center_line
    output_center_line = os.path.join(cellPathEdited, fileName+"_output_center_line"+extension+".shp")
    global output_line_footprint
    output_line_footprint = os.path.join(cellPathEdited, fileName+"_output_footprint"+extension+".shp")

    # Generate cost raster
    print("Cell {} canopy cost tool started.".format(fileName))
    #CanopyCost()
    print("Cell {} canopy cost tool finished.".format(fileName))

    # Generate center line
    print("Cell {} centerline tool started.".format(fileName))
    CenterLine()
    print("Cell {} centerline tool finished.".format(fileName))

    return output_center_line


def ProcessCells(cells, paramsList, basePath, discriminateLineType=False):
    """ This function will traverse all cells in cellFile (from plan data), clip seismic lines and CHM rasters
        in cells and generate center lines
        lineFile: seismic line file
        cellFile: cell file
    """
    for cell in cells:

        # only process region 3, block 2
        #if cell[0] != 3 or cell[1] != 2 or cell[2] not in range(31, 32):
        #    continue

        cellFolder = os.path.join("Region_" + str(cell[0]), "Block_" + str(cell[1]), "Cell_" + (str(cell[2])).zfill(2))
        cellPath = os.path.join(basePath, cellFolder)
        cellString = list(map(str, cell))
        cellString[2] = cellString[2].zfill(2)
        fileName = '_'.join(cellString)

        if discriminateLineType:
            outputLineFiles = []
            for i in range(0, 3):
                fileTemp = ProcessCell(cellPath, fileName, paramsList, paramsList[i])
                outputLineFiles.append(fileTemp)
                # Merge three types of output line
                outputCenterLine = os.path.join(cellPath, fileName + "_output_center_line.shp")
                arcpy.Merge_management(outputLineFiles, outputCenterLine)
        else:
            ProcessCell(cellPath, fileName, paramsList, "default")

            # Prepare ArcGIS Pro project
            #PrepareArcGISproProject(cellPath, fileName)

        print("Cell {} processed".format('_'.join(map(str, cell))))

def main():

    """ Prepare input seismic lines and raster for each cell"""

    # Add Scripts folder to sys.path
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

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

    #cells = [(x, y, z) for x in range(3,4) for y in range(2,3) for z in range(30, 31)]
    cells = [(3, 2, 32)]
    paramsList = {"conventional": ("2", "3", "10", "0.3", "1.5", "30", "32", "True", r""),
              "low_impact": ("2", "3", "10", "0.3", "1.5", "30", "32", "True", r""),
              "trail": ("2", "3", "10", "0.3", "1.5", "30", "32", "True", r""),
              "default": ("2", "3", "10", "0.3", "1.5", "30", "32", "True", r"")}

    discriminateLineType = False
    ProcessCells(cells, paramsList, basePath, discriminateLineType)


if __name__ == "__main__":
    main()
