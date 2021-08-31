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
# FLM_ForestLineAttributes.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Calculates a series of attributes related to forest line shape, 
# size and microtopography.
#
# ---------------------------------------------------------------------------
# System imports
import multiprocessing
import math

# ArcGIS imports
import arcpy
arcpy.CheckOutExtension("Spatial")

# Local imports
import FLM_Common as flmc
import FLM_Attribute_Functions as flma

workspaceName = "FLM_SLA_output"


def workLines(lineNo):
    outWorkspace = flmc.GetWorkspace(workspaceName)
    f = open(outWorkspace + "\\params.txt")

    outWorkspace = f.readline().strip()
    Input_Lines = f.readline().strip()
    Input_Footprint = f.readline().strip()
    Input_CHM = f.readline().strip()
    SamplingType = f.readline().strip()
    Segment_Length = float(f.readline().strip())
    Tolerance_Radius = float(f.readline().strip())
    LineSearchRadius = float(f.readline().strip())
    Attributed_Segments = f.readline().strip()
    areaAnalysis = True if f.readline().strip() == "True" else False
    heightAnalysis = True if f.readline().strip() == "True" else False
    f.close()

    # Temporary files
    lineSeg = outWorkspace + "\\FLM_SLA_Segment_" + str(lineNo) + ".shp"
    lineBuffer = outWorkspace + "\\FLM_SLA_Buffer_" + str(lineNo) + ".shp"
    lineClip = outWorkspace + "\\FLM_SLA_Clip_" + str(lineNo) + ".shp"
    lineStats = outWorkspace + "\\FLM_SLA_Stats_" + str(lineNo) + ".dbf"

    if areaAnalysis:
        arcpy.Buffer_analysis(lineSeg, lineBuffer, LineSearchRadius, line_side="FULL", line_end_type="FLAT",
                              dissolve_option="NONE", dissolve_field="", method="PLANAR")
        arcpy.Clip_analysis(Input_Footprint, lineBuffer, lineClip)
        arcpy.Delete_management(lineBuffer)
        if heightAnalysis and arcpy.Exists(lineClip):
            try:
                arcpy.gp.ZonalStatisticsAsTable_sa(lineClip, arcpy.Describe(lineClip).OIDFieldName,
                                                   Input_CHM, lineStats, "DATA", "ALL")
            except Exception as e:
                lineStats = ""
                print(e)

    rows = arcpy.UpdateCursor(lineSeg)
    shapeField = arcpy.Describe(lineSeg).ShapeFieldName
    row = rows.next()

    feat = row.getValue(shapeField)  # creates a geometry object
    length = float(row.getValue("LENGTH"))  # creates a geometry object

    try:
        bearing = float(row.getValue("BEARING"))  # creates a geometry object
    except Exception as e:
        bearing = 0
        print(e)

    segmentnum = 0
    segment_list = []
    for segment in feat:  # loops through every segment in a line
        # loops through every vertex of every segment
        # get.PArt returns an array of points for a particular part in the geometry
        for pnt in feat.getPart(segmentnum):
            if pnt:  # adds all the vertices to segment_list, which creates an array
                segment_list.append(arcpy.Point(float(pnt.X), float(pnt.Y)))

    # Sinuosity calculation
    eucDistance = arcpy.PointGeometry(feat.firstPoint).distanceTo(arcpy.PointGeometry(feat.lastPoint))
    try:
        row.setValue("Sinuosity", length / eucDistance)
    except Exception as e:
        row.setValue("Sinuosity", float("inf"))
        print(e)

    # Direction based on bearing
    ori = "N-S"
    if 22.5 <= bearing < 67.5 or 202.5 <= bearing < 247.5:
        ori = "NE-SW"
    elif 67.5 <= bearing < 112.5 or 247.5 <= bearing < 292.5:
        ori = "E-W"
    elif 112.5 <= bearing < 157.5 or 292.5 <= bearing < 337.5:
        ori = "NW-SE"
    row.setValue("Direction", ori)

    # If footprint polygons are available, get area-based variables
    if areaAnalysis:
        totalArea = float(row.getValue("POLY_AREA"))
        totalPerim = float(row.getValue("PERIMETER"))

        row.setValue("AvgWidth", totalArea / length)

        try:
            row.setValue("Fragment", totalPerim / totalArea)
        except Exception as e:
            row.setValue("Fragment", float("inf"))

        if arcpy.Exists(lineStats):
            # Retrieve useful stats from table which are used to derive CHM attributes
            ChmFootprintCursor = arcpy.SearchCursor(lineStats)
            ChmFoot = ChmFootprintCursor.next()
            chm_count = float(ChmFoot.getValue("COUNT"))
            chm_area = float(ChmFoot.getValue("AREA"))
            chm_mean = float(ChmFoot.getValue("MEAN"))
            chm_std = float(ChmFoot.getValue("STD"))
            chm_sum = float(ChmFoot.getValue("SUM"))
            del ChmFootprintCursor

            # Average vegetation height directly obtained from CHM mean
            row.setValue("AvgHeight", chm_mean)

            # Cell area obtained via dividing the total area by the number of cells
            # (this assumes that the projection is UTM to obtain a measure in square meters)
            cellArea = chm_area / chm_count

            # CHM volume (3D) is obtained via multiplying the sum of height (1D) of all cells
            # of all cells within the footprint by the area of each cell (2D)
            row.setValue("Volume", chm_sum * cellArea)

            # The following math is performed to use available stats (fast) and avoid further
            # raster sampling procedures (slow).
            # RMSH is equal to the square root of the sum of the squared mean and
            # the squared standard deviation (population)
            # STD of population (n) is derived from the STD of sample (n-1).
            # This number is not useful by itself, only to derive RMSH.
            sqStdPop = math.pow(chm_std, 2) * (chm_count - 1) / chm_count

            # Obtain RMSH from mean and STD
            row.setValue("Roughness", math.sqrt(math.pow(chm_mean, 2) + sqStdPop))

    rows.updateRow(row)

    del row, rows
    # Clean temporary files
    if arcpy.Exists(lineClip):
        arcpy.Delete_management(lineClip)
    if arcpy.Exists(lineStats):
        arcpy.Delete_management(lineStats)


def workLinesMem(segment_info):
    """
    New version of worklines. It uses memory workspace instead of shapefiles.
    The refactoring is to accelerate the processing speed.
    """

    # input verification
    if segment_info is None or len(segment_info) <= 1:
        print("Input segment is corrupted, ignore")

    outWorkspace = flmc.GetWorkspace(workspaceName)
    f = open(outWorkspace + "\\params.txt")

    outWorkspace = f.readline().strip()
    Input_Lines = f.readline().strip()
    Input_Footprint = f.readline().strip()
    Input_CHM = f.readline().strip()
    SamplingType = f.readline().strip()
    Segment_Length = float(f.readline().strip())
    Tolerance_Radius = float(f.readline().strip())
    LineSearchRadius = float(f.readline().strip())
    Attributed_Segments = f.readline().strip()
    areaAnalysis = True if f.readline().strip() == "True" else False
    heightAnalysis = True if f.readline().strip() == "True" else False
    f.close()

    line = [segment_info[1]]
    attributes = ["SHAPE@"]
    lineNo = segment_info[1]  # second element is the line No.
    outWorkspaceMem = r"memory"
    arcpy.env.workspace = r"memory"

    # Temporary files
    lineSeg = os.path.join(outWorkspaceMem, "FLM_SLA_Segment_" + str(lineNo))
    lineBuffer = os.path.join(outWorkspaceMem, "FLM_SLA_Buffer_" + str(lineNo))
    lineClip = os.path.join(outWorkspaceMem, "FLM_SLA_Clip_" + str(lineNo))
    lineStats = os.path.join(outWorkspaceMem, "FLM_SLA_Stats_" + str(lineNo))

    if areaAnalysis:
        arcpy.Buffer_analysis(line, lineBuffer, LineSearchRadius, line_side="FULL", line_end_type="FLAT",
                              dissolve_option="NONE", dissolve_field="", method="PLANAR")
        arcpy.Clip_analysis(Input_Footprint, lineBuffer, lineClip)
        arcpy.Delete_management(lineBuffer)
        if heightAnalysis and arcpy.Exists(lineClip):
            try:
                arcpy.gp.ZonalStatisticsAsTable_sa(lineClip, arcpy.Describe(lineClip).OIDFieldName,
                                                   Input_CHM, lineStats, "DATA", "ALL")
            except Exception as e:
                lineStats = ""
                print(e)

    rows = arcpy.UpdateCursor(lineSeg)
    shapeField = arcpy.Describe(lineSeg).ShapeFieldName
    row = rows.next()

    feat = row.getValue(shapeField)  # creates a geometry object
    length = float(row.getValue("LENGTH"))  # creates a geometry object

    try:
        bearing = float(row.getValue("BEARING"))  # creates a geometry object
    except Exception as e:
        bearing = 0
        print(e)

    segmentnum = 0
    segment_list = []
    for segment in feat:  # loops through every segment in a line
        # loops through every vertex of every segment
        # get.PArt returns an array of points for a particular part in the geometry
        for pnt in feat.getPart(segmentnum):
            if pnt:  # adds all the vertices to segment_list, which creates an array
                segment_list.append(arcpy.Point(float(pnt.X), float(pnt.Y)))

    # Sinuosity calculation
    eucDistance = arcpy.PointGeometry(feat.firstPoint).distanceTo(arcpy.PointGeometry(feat.lastPoint))
    try:
        row.setValue("Sinuosity", length / eucDistance)
    except Exception as e:
        row.setValue("Sinuosity", float("inf"))
        print(e)

    # Direction based on bearing
    ori = "N-S"
    if 22.5 <= bearing < 67.5 or 202.5 <= bearing < 247.5:
        ori = "NE-SW"
    elif 67.5 <= bearing < 112.5 or 247.5 <= bearing < 292.5:
        ori = "E-W"
    elif 112.5 <= bearing < 157.5 or 292.5 <= bearing < 337.5:
        ori = "NW-SE"
    row.setValue("Direction", ori)

    # If footprint polygons are available, get area-based variables
    if areaAnalysis:
        totalArea = float(row.getValue("POLY_AREA"))
        totalPerim = float(row.getValue("PERIMETER"))

        row.setValue("AvgWidth", totalArea / length)

        try:
            row.setValue("Fragment", totalPerim / totalArea)
        except Exception as e:
            row.setValue("Fragment", float("inf"))

        if arcpy.Exists(lineStats):
            # Retrieve useful stats from table which are used to derive CHM attributes
            ChmFootprintCursor = arcpy.SearchCursor(lineStats)
            ChmFoot = ChmFootprintCursor.next()
            chm_count = float(ChmFoot.getValue("COUNT"))
            chm_area = float(ChmFoot.getValue("AREA"))
            chm_mean = float(ChmFoot.getValue("MEAN"))
            chm_std = float(ChmFoot.getValue("STD"))
            chm_sum = float(ChmFoot.getValue("SUM"))
            del ChmFootprintCursor

            # Average vegetation height directly obtained from CHM mean
            row.setValue("AvgHeight", chm_mean)

            # Cell area obtained via dividing the total area by the number of cells
            # (this assumes that the projection is UTM to obtain a measure in square meters)
            cellArea = chm_area / chm_count

            # CHM volume (3D) is obtained via multiplying the sum of height (1D) of all cells
            # of all cells within the footprint by the area of each cell (2D)
            row.setValue("Volume", chm_sum * cellArea)

            # The following math is performed to use available stats (fast) and avoid further
            # raster sampling procedures (slow).
            # RMSH is equal to the square root of the sum of the squared mean and
            # the squared standard deviation (population)
            # STD of population (n) is derived from the STD of sample (n-1).
            # This number is not useful by itself, only to derive RMSH.
            sqStdPop = math.pow(chm_std, 2) * (chm_count - 1) / chm_count

            # Obtain RMSH from mean and STD
            row.setValue("Roughness", math.sqrt(math.pow(chm_mean, 2) + sqStdPop))

    rows.updateRow(row)

    del row, rows
    # Clean temporary files
    if arcpy.Exists(lineClip):
        arcpy.Delete_management(lineClip)
    if arcpy.Exists(lineStats):
        arcpy.Delete_management(lineStats)


def main(argv=None):
    # Setup script path and workspace folder
    global outWorkspace
    outWorkspace = flmc.SetupWorkspace(workspaceName)

    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_FLA_params.txt")

    # Tool arguments
    Input_Lines = args[0].rstrip()
    Input_Footprint = args[1].rstrip()
    Input_CHM = args[2].rstrip()
    SamplingType = args[3].rstrip()
    Segment_Length = float(args[4].rstrip())
    Tolerance_Radius = float(args[5].rstrip())
    LineSearchRadius = float(args[6].rstrip())
    Attributed_Segments = args[7].rstrip()

    areaAnalysis = arcpy.Exists(Input_Footprint)
    heightAnalysis = arcpy.Exists(Input_CHM)

    # write params to text file
    f = open(outWorkspace + "\\params.txt", "w")
    f.write(outWorkspace + "\n")
    f.write(Input_Lines + "\n")
    f.write(Input_Footprint + "\n")
    f.write(Input_CHM + "\n")
    f.write(SamplingType + "\n")
    f.write(str(Segment_Length) + "\n")
    f.write(str(Tolerance_Radius) + "\n")
    f.write(str(LineSearchRadius) + "\n")
    f.write(Attributed_Segments + "\n")
    f.write(str(areaAnalysis) + "\n")
    f.write(str(heightAnalysis) + "\n")
    f.close()

    # Temporary layers
    fileBuffer = outWorkspace + "\\FLM_SLA_Buffer.shp"
    fileIdentity = outWorkspace + "\\FLM_SLA_Identity.shp"
    fileFootprints = outWorkspace + "\\FLM_SLA_Footprints.shp"

    footprintField = flmc.FileToField(fileBuffer)

    flmc.log("Preparing line segments...")
    # Segment lines
    flmc.log("FlmLineSplit: Input_Lines = " + Input_Lines)
    SLA_Segmented_Lines = flma.FlmLineSplit(outWorkspace, Input_Lines, SamplingType, Segment_Length, Tolerance_Radius)
    flmc.logStep("Line segmentation")

    # Linear attributes
    flmc.log("Adding attributes...")
    arcpy.AddGeometryAttributes_management(SLA_Segmented_Lines, "LENGTH;LINE_BEARING", "METERS")

    if areaAnalysis:
        arcpy.Buffer_analysis(SLA_Segmented_Lines, fileBuffer, LineSearchRadius, line_side="FULL",
                              line_end_type="FLAT", dissolve_option="NONE", dissolve_field="", method="PLANAR")
        arcpy.Identity_analysis(Input_Footprint, fileBuffer, fileIdentity, join_attributes="ONLY_FID",
                                cluster_tolerance="", relationship="NO_RELATIONSHIPS")
        arcpy.Dissolve_management(fileIdentity, fileFootprints, dissolve_field=footprintField,
                                  statistics_fields="", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
        arcpy.JoinField_management(fileFootprints, footprintField, fileBuffer,
                                   arcpy.Describe(fileBuffer).OIDFieldName, fields="ORIG_FID")
        fCursor = arcpy.UpdateCursor(fileFootprints)
        for row in fCursor:
            if float(row.getValue(footprintField)) < 0:
                fCursor.deleteRow(row)
        del fCursor

        arcpy.AddGeometryAttributes_management(fileFootprints, Geometry_Properties="AREA;PERIMETER_LENGTH",
                                               Length_Unit="METERS", Area_Unit="SQUARE_METERS", Coordinate_System="")
        arcpy.JoinField_management(SLA_Segmented_Lines, arcpy.Describe(SLA_Segmented_Lines).OIDFieldName,
                                   fileFootprints, "ORIG_FID", fields="POLY_AREA;PERIMETER")

        arcpy.Delete_management(fileBuffer)
        arcpy.Delete_management(fileIdentity)
        arcpy.Delete_management(fileFootprints)

    # Add other fields
    keepFields = ["LENGTH", "BEARING"]
    if areaAnalysis:
        keepFields += ["POLY_AREA", "PERIMETER"]

    arcpy.AddField_management(SLA_Segmented_Lines, "Direction", "TEXT")
    arcpy.AddField_management(SLA_Segmented_Lines, "Sinuosity", "DOUBLE")
    keepFields += ["Direction", "Sinuosity"]

    if areaAnalysis:
        arcpy.AddField_management(SLA_Segmented_Lines, "AvgWidth", "DOUBLE")
        arcpy.AddField_management(SLA_Segmented_Lines, "Fragment", "DOUBLE")
        keepFields += ["AvgWidth", "Fragment"]
        if heightAnalysis:
            arcpy.AddField_management(SLA_Segmented_Lines, "AvgHeight", "DOUBLE")
            arcpy.AddField_management(SLA_Segmented_Lines, "Volume", "DOUBLE")
            arcpy.AddField_management(SLA_Segmented_Lines, "Roughness", "DOUBLE")
            keepFields += ["AvgHeight", "Volume", "Roughness"]

    # Prepare input lines for multiprocessing
    # ["Direction","Sinuosity","Area","AvgWidth","Perimeter","Fragment","SLA_Unity","AvgHeight","Volume","Roughness"])
    segment_all = flmc.SplitLines(SLA_Segmented_Lines, outWorkspace, "SLA", False, keepFields)

    arcpy.Delete_management(SLA_Segmented_Lines)

    pool = multiprocessing.Pool(processes=flmc.GetCores())
    flmc.log("Multiprocessing lines...")
    # pool.map(workLinesMem, range(1, numLines + 1))
    line_attributes = pool.map(workLinesMem, segment_all)
    pool.close()
    pool.join()

    flmc.logStep("Line attributes multiprocessing")

    # Create output line attribute shapefile
    flmc.log("Create line attribute shapefile...")
    try:
        arcpy.CreateFeatureclass_management(os.path.dirname(Attributed_Segments), os.path.basename(Attributed_Segments),
                                            "POLYLINE", Input_Lines, "DISABLED", "DISABLED", Input_Lines)
    except Exception as e:
        print("Create feature class {} failed.".format(Attributed_Segments))
        print(e)
        return

    # Flatten line attribute which is a list of list
    flmc.log("Writing line attributes to shapefile...")
    # TODO: is this necessary? Since we need list of single line next
    cl_list = [item for sublist in centerlines for item in sublist]
    with arcpy.da.InsertCursor(Attributed_Segments, keepFields) as cursor:
        for line in cl_list:
            cursor.insertRow([line])

    flmc.logStep("Line attribute file: {} done".format())

