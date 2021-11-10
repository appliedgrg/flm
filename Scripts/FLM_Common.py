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
# FLM_Common.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: This script contains common functions used by many FLM tools.
# Many functions are dedicated to setting up workspace and logging text.
# Of special importance is the SplitLines function which prepares an
# input polyline shapefile for multiprocessing.
#
# ---------------------------------------------------------------------------
# System imports
import time
import os
import sys
import multiprocessing

# ArcGIS imports
import arcpy

try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

timeStart = time.clock()
timeLast = timeStart
scriptPath = os.path.dirname(os.path.realpath(__file__))
coresFile = "mpc.txt"

USE_MEMORY_WORKSPACE = 1  # switch of using memory workspace or not

def logStart(tool):
    log("----------")
    global timeStart, timeLast
    timeStart = time.clock()
    timeLast = timeStart
    log("Running tool: "+tool.title)
    log("Processing initiated at: "+time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime()))
    log("----------")
    log("TOOL PARAMETERS")
    params = tool.GetParams()
    for i in range(0, len(tool.input)):
        log(tool.fields[i]+": "+params[i])
    log("----------")


def logStep(stepName):
    global timeLast
    timeThis = time.clock()
    log(stepName+" is done! Execution time: "+"{:.2f}".format(timeThis-timeLast)+" seconds")
    timeLast = timeThis
    log("----------")


def logEnd(tool):
    log("\nTool "+tool.title+" has executed successfully!")
    timeEnd = time.clock()
    global timeStart
    log("Total Execution Time: "+"{:.2f}".format(timeEnd-timeStart)+" seconds")


def log(text, onlyFile = False):
    if(onlyFile == False):
        print(text)
    text_file = open(r"log.txt", "a")
    text_file.write(text+"\n")
    text_file.close()
    del text_file


def refreshLog():
    text_file = open(r"log.txt", "w")
    text_file.write("")
    text_file.close()
    del text_file


def newLog(version):
    text_file = open(r"log.txt", "a")
    text_file.write("\n\n###\n\n\n")
    text_file.close()
    log("Forest Line Mapper v. "+str(version))
    log("Python "+str(sys.version))
    log("Time: "+time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime()))
    del text_file


def PathFileName (path):
    return os.path.basename(path)


def FileToField(filen):
    return ("FID_"+os.path.basename(os.path.splitext(filen)[0]).replace(" ", "_"))[:10]


def GetArgs(paramFile):
    # Load arguments from file
    try:
        paramFile = scriptPath+"\\"+paramFile
        pfile = open(paramFile, "r")
        args = pfile.readlines()
        pfile.close()
        return args
    except Exception as e:
        return ["-1"]*100


def SetArgs(paramFile, args):
        paramFile = scriptPath+"\\"+paramFile
        pfile = open(paramFile, "w")
        for arg in args:
            pfile.write(str(arg)+"\n")
        pfile.close()


def GetCores():
    maxCores = multiprocessing.cpu_count()
    coresPath = scriptPath+"\\"+coresFile
    try:
        cfile = open(coresPath, "r")
        args = cfile.readlines()
        cfile.close()
        cores = int(args[0])
        if cores>0 and cores<=maxCores:
            return cores
        else:
            cfile = open(coresPath, "w")
            cfile.write(str(maxCores))
            cfile.close()
            return maxCores
    except Exception as e:
        cfile = open(coresPath, "w")
        cfile.write(str(maxCores))
        cfile.close()
        return maxCores


def SetCores(cores):
    coresPath = scriptPath+"\\"+coresFile
    cfile = open(coresPath, "w")
    cfile.write(str(cores))
    cfile.close()


def SetupWorkspace (outWorkName):
    """
    This function creates a folder outWorkName in the scriptPath folder.
    If it already exists, all shapefiles and rasters in it are deleted.
    """
    import arcpy
    
    outWorkspace = scriptPath + "\\" + outWorkName
    
    # Setup output folder
    try:
        # arcpy.CreateFileGDB_management(scriptPath, outWorkName +".gdb")
        os.mkdir(outWorkspace)
        log("Scratch workspace " + str(outWorkspace) + " created.")
    except Exception as e:
        log("Scratch workspace " + str(outWorkspace) + " already exists.")

    arcpy.env.workspace = outWorkspace

    # Delete old files
    oldShapefiles = arcpy.ListFeatureClasses()
    if len(oldShapefiles) > 0:
        log("There are "+str(len(oldShapefiles))+" old shapefiles in workspace folder. These will be deleted.")
        for fc in oldShapefiles:
            arcpy.Delete_management(fc)
    del oldShapefiles

    oldRasters = arcpy.ListRasters()
    if len(oldRasters) > 0:
        log("There are "+str(len(oldRasters))+" old rasters in workspace folder. These will be deleted.")
        for ras in oldRasters:
            arcpy.Delete_management(ras)
    del oldRasters

    logStep("Workspace Setup")

    return outWorkspace


def GetWorkspace(outWorkName):
    outWorkspace = scriptPath + "\\" + outWorkName
    return outWorkspace


def SplitLines(linesFc, outWorkspace, toolCodename, ProcessSegments, polygons=None, KeepFieldName=None):
    """
    This function splits the input polyline shapefile (linesFc) into several shapefiles.
    ProcessSegments:
      False: shapefile will be created for each feature.
      True:  one shapefile will be created for each pair of vertices in the input lines.

      outWorkspace: where files are placed in
      toolCodename: base name to make subfolder for tools in workspace in format FLM_toolCodename_output
      KeepFieldName: fields to transfer from the inputs to the outputs.
      polygons: list of lidar coverage polygon geometry with year [(polygon geometry, year), ...]

    Return:
      numLines: total number of segments cached
      all_segments: all segment polylines in a list which is intended to be used in multiprocessing
    """

    if KeepFieldName is None:
        KeepFieldName = []
    elif isinstance(KeepFieldName, str):
        KeepFieldName = [KeepFieldName]

    # Create search cursor on input center lines file
    line = 0
    rows = arcpy.SearchCursor(linesFc)
    all_segments = []  # return all segment polylines

    # Separates the input feature class into multiple feature classes,
    # each containing a single line, hereby referenced as "segment"
    log("Lines Setup...")

    desc = arcpy.Describe(linesFc)
    fieldDict = {}
    for field in desc.fields:
        fieldDict[field.name] = field.type

    shapeField = desc.ShapeFieldName
    del desc

    for row in rows:
        feat = row.getValue(shapeField)   # creates a geometry object

        KeepField = []
        for fieldName in KeepFieldName:
            KeepField.append(row.getValue(fieldName))

        segmentnum = 0
        for segment in feat:  # loops through every segment in a line
            segment_list = []
            # loops through every vertex of every segment
            # get.PArt returns an array of points for a particular part in the geometry
            for pnt in feat.getPart(segmentnum):
                if pnt:	 # adds all the vertices to segment_list, which creates an array
                    segment_list.append(arcpy.Point(float(pnt.X), float(pnt.Y)))

            segmentnum += 1

            # loops through every vertex in the list   #-1 is done
            # so the second last vertex is the start of a segment and the code is within range...
            for vertexID in range(0, len(segment_list)-1):
                line += 1
                segment_fname = "FLM_"+toolCodename + "_Segment_" + str(line) + ".shp"
                segment_fpath = outWorkspace + "\\" + segment_fname
                if arcpy.Exists(segment_fpath):
                    arcpy.Delete_management(segment_fpath)

                try:
                    if not USE_MEMORY_WORKSPACE:  # Use memory workspace
                        arcpy.CreateFeatureclass_management(outWorkspace, segment_fname, "POLYLINE",
                                                            "", "DISABLED", "DISABLED", linesFc)

                        for fieldName in KeepFieldName:
                            if(fieldName in fieldDict):
                                arcpy.AddField_management(outWorkspace+"\\"+segment_fname,
                                                          fieldName, fieldDict[fieldName])

                        cursor = arcpy.da.InsertCursor(segment_fpath, KeepFieldName+["SHAPE@"])

                    if not ProcessSegments:
                        array = arcpy.Array(segment_list)
                    else:
                        array = arcpy.Array()
                        array.add(segment_list[vertexID])
                        array.add(segment_list[vertexID+1])
                    polyline = arcpy.Polyline(array, arcpy.Describe(linesFc).spatialReference)
                    # add segments and attributes for later return
                    all_segments.append([polyline, line, dict(zip(KeepFieldName, KeepField)), polygons])

                    if not USE_MEMORY_WORKSPACE:
                        cursor.insertRow(KeepField+[polyline])

                        del cursor

                    if not ProcessSegments:
                        break
                except Exception as e:
                    print("Creating segment feature class failed: " + segment_fname + ".")
                    print(e)

    del rows

    # At this point all lines have been separated into different feature classes located at the scratch workspace
    numLines = line
    log("There are " + str(numLines) + " lines to process.")
    logStep("Line Setup")
    return all_segments


def SplitFeature (fc, idField, outWorkspace, toolCodename):
    import arcpy

    # Create search cursor on input center lines file
    rows = arcpy.SearchCursor(fc)

    log("Splitting Feature...")

    desc = arcpy.Describe(fc)
    shapeField = desc.ShapeFieldName
    shapeType = desc.shapeType
    del desc

    for row in rows:
        feat = row.getValue(shapeField)   # creates a geometry object
        name = row.getValue(idField)   # creates a geometry object
        ()
        segment_fname = "FLM_"+toolCodename +"_Split_"+ str(name) + ".shp"
        segment_fpath = outWorkspace +"\\"+ segment_fname
        if arcpy.Exists(segment_fpath):
            arcpy.Delete_management(segment_fpath)

        arcpy.CreateFeatureclass_management(outWorkspace, segment_fname, shapeType, "", "DISABLED", "DISABLED", fc)
        cursor = arcpy.da.InsertCursor(segment_fpath, ["SHAPE@"])
        cursor.insertRow([feat])

        del cursor

    del rows

    logStep("Feature Split")

