#
#    Copyright (C) 2021  Applied Geospatial Research Group
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
# FLM_VertexOptimization.py
# Script Author: Richard Zeng
# Date: 2021-Oct-26
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Move line vertices to right seismic line courses
#
# ---------------------------------------------------------------------------
# System imports
import os
import multiprocessing
import numpy as np
import math
import uuid
import shapely.geometry as shgeo

# ArcGIS imports
import arcpy
from arcpy.sa import *

# Local imports
arcpy.CheckOutExtension("Spatial")
import FLM_Common as flmc

workspaceName = "FLM_VO_output"
DISTANCE_THRESHOLD = 2  # 1 meter for intersection neighbourhood
SEGMENT_LENGTH = 20  # Distance (meter) from intersection to anchor points
EPSILON = 1e-9


def PathFile(path):
    return path[path.rfind("\\") + 1:]


def updatePtInLines(pt_array, index, point):

    if point:
        if index == 0 or index == -1:
        # the first point of first part
        # or the last point of the last part
            replace_index = 0
            if index == -1:
                try:
                    replace_index = len(pt_array[index])-1
                except Exception as e:
                    print(e)

            try:
                pt_array[index].replace(replace_index, arcpy.Point(point[0], point[1]))
            except Exception as e:
                print(e)

    return pt_array


def arcpyLineToPlainLine(line):
    if not line:
        return

    plain_line = []
    for part in line:
        if not part:
            continue
        for pt in part:
            plain_line.append((pt.X, pt.Y))

    return shgeo.LineString(plain_line)


def intersectionOfLines(line_1, line_2):
    line_1 = arcpyLineToPlainLine(line_1[0])
    line_2 = arcpyLineToPlainLine(line_2[0])

    # intersection collection, may contain points and lines
    inter = None
    if line_1 and line_2:
        inter = line_1.intersection(line_2)

    if inter:
        return inter.centroid.x, inter.centroid.y

    return inter


def closestPointToLine(point, line):
    if not line:
        return
    if not line[0]:
        return

    pt_list = []
    for part in line[0]:
        for pt in part:
            pt_list.append([pt.X, pt.Y])

    line_string = shgeo.LineString(pt_list)
    pt = line_string.interpolate(line_string.project(shgeo.Point(point)))

    return pt.x, pt.y


def appendToGroup(vertex, vertex_grp):
    """
    Append new vertex to vertex group, by calculating distance to existing vertices
    """
    pt_added = False
    global DISTANCE_THRESHOLD
    global SEGMENT_LENGTH

    # Calculate anchor point for each vertex
    point = arcpy.Point(vertex["point"][0], vertex["point"][1])
    line = vertex["lines"][0][0]
    index = vertex["lines"][0][1]
    pts = ptsInLine(line)

    if index == 0:
        pt_1 = point
        pt_2 = pts[1]
    elif index == -1:
        pt_1 = point
        pt_2 = pts[-2]

    dist_pt = math.sqrt(sum((px - qx) ** 2.0 for px, qx in zip([pt_1.X, pt_1.Y], [pt_2.X, pt_2.Y])))
    X = pt_1.X + (pt_2.X - pt_1.X) * SEGMENT_LENGTH / dist_pt
    Y = pt_1.Y + (pt_2.Y - pt_1.Y) * SEGMENT_LENGTH / dist_pt
    vertex["lines"][0].insert(-1, [X, Y])  # add anchor point to list (the third element)

    for item in vertex_grp:
        if abs(point.X - item["point"][0]) < DISTANCE_THRESHOLD and abs(
                point.Y - item["point"][1]) < DISTANCE_THRESHOLD:
            item["lines"].append(vertex["lines"][0])
            pt_added = True

    # Add the first vertex or new vertex not found neighbour
    if not pt_added:
        vertex_grp.append(vertex)


def ptsInLine(line):
    point_list = []
    for part in line:
        for point in part:  # loops through every point in a line
            # loops through every vertex of every segment
            if point:  # adds all the vertices to segment_list, which creates an array
                point_list.append(point)

    return point_list


def groupIntersections(lines):
    """
    Identify intersections of 2,3 or 4 lines and group them.
    Each group has all the end vertices, start(0) or end (-1) vertex and the line geometry
    Intersection list format: {["point":intersection_pt, "lines":[[line_geom, pt_index, anchor_geom], ...]], ...}
    pt_index: 0 is start vertex, -1 is end vertex
    """
    vertex_grp = []

    for line in lines:
        point_list = ptsInLine(line[0])

        # Find origin and destination coordinates
        pt_start = {"point": [point_list[0].X, point_list[0].Y], "lines": [[line[0], 0, {"lineNo": line[1]}]]}
        pt_end = {"point": [point_list[-1].X, point_list[-1].Y], "lines": [[line[0], -1, {"lineNo": line[1]}]]}
        appendToGroup(pt_start, vertex_grp)
        appendToGroup(pt_end, vertex_grp)

    return vertex_grp


def getSlope(line, end_index):
    """
    Calculate the slope of the first or last segment
    line: ArcPy Polyline
    end_index: 0 or -1 of the the line vertices. Consider the multipart.
    """
    global EPSILON

    pt = ptsInLine(line)

    if end_index == 0:
        pt_1 = pt[0]
        pt_2 = pt[1]
    elif end_index == -1:
        pt_1 = pt[-1]
        pt_2 = pt[-2]

    if math.isclose(pt_1.X, pt_2.X, abs_tol=EPSILON):
        return math.inf
    else:
        return (pt_1.Y - pt_2.Y) / (pt_1.X - pt_2.X)


def generateAnchorPairs(vertex):
    """
    Extend line following outward direction to length of SEGMENT_LENGTH
    Use the end point as anchor point.
        vertex: input intersection with all related lines
        return: one or two pairs of anchors according to numbers of lines intersected.
                two pairs anchors return when 3 or 4 lines intersected
                one pair anchors return when 1 or 2 lines intersected
    """
    lines = vertex["lines"]
    slopes = []
    for line in lines:
        line_seg = line[0]
        pt_index = line[1]
        slopes.append(getSlope(line_seg, pt_index))

    index = 0  # the index of line which paired with first line.
    pt_start_1 = None
    pt_end_1 = None
    pt_start_2 = None
    pt_end_2 = None

    if len(slopes) == 4 or len(slopes) == 3:
        diff = [abs(slopes[0] - i) for i in slopes[1:]]  # calculate difference of first slopes with the rest
        index = np.argmin(diff) + 1  # 1, 2, oor 3

        # first anchor pair
        pt_start_1 = lines[0][2]
        pt_end_1 = lines[index][2]

        # the rest one or two index
        a = {0, 1, 2, 3}
        b = set([0, index])
        remains = list(a.difference(b))  # the remaining index

        try:
            if len(remains) == 2:
                pt_start_2 = lines[remains[0]][2]
                pt_end_2 = lines[remains[1]][2]
            elif len(remains) == 1:
                pt_start_2 = lines[remains[0]][2]
                # symmetry point of pt_start_2 regarding vertex["point"]
                X = vertex["point"][0] - (pt_start_2[0] - vertex["point"][0])
                Y = vertex["point"][1] - (pt_start_2[1] - vertex["point"][1])
                pt_end_2 = [X, Y]
        except Exception as e:
            print(e)

    # this scenario only use two anchors and find closest point on least cost path
    if len(slopes) == 2:
        pt_start_1 = lines[0][2]
        pt_end_1 = lines[1][2]
    elif len(slopes) == 1:
        pt_start_1 = lines[0][2]
        # symmetry point of pt_start_1 regarding vertex["point"]
        X = vertex["point"][0] - (pt_start_1[0] - vertex["point"][0])
        Y = vertex["point"][1] - (pt_start_1[1] - vertex["point"][1])
        pt_end_1 = [X, Y]

    if not pt_start_1 or not pt_end_1:
        print("Anchors not found")

    if len(slopes) == 4 or len(slopes) == 3:
        return pt_start_1, pt_end_1, pt_start_2, pt_end_2
    elif len(slopes) == 2 or len(slopes) == 1:
        return pt_start_1, pt_end_1


def leastCostPath(Cost_Raster, anchors, Line_Processing_Radius):
    """
    Calculate least cost path between two points
        Cost_Raster: cost raster
        anchors: list of two points: start and end points
        Line_Processing_Radius
    """
    if not anchors[0] or not anchors[1]:
        print("Anchor points not valid")
        centerline = [None]
        return centerline

    lineNo = uuid.uuid4().hex  # random line No.
    outWorkspaceMem = r"memory"
    arcpy.env.workspace = r"memory"

    fileClip = os.path.join(outWorkspaceMem, "FLM_VO_Clip_" + str(lineNo) + ".tif")
    fileCostDist = os.path.join(outWorkspaceMem, "FLM_VO_CostDist_" + str(lineNo) + ".tif")
    fileCostBack = os.path.join(outWorkspaceMem, "FLM_VO_CostBack_" + str(lineNo) + ".tif")
    fileCenterline = os.path.join(outWorkspaceMem, "FLM_VO_Centerline_" + str(lineNo))

    # line from points
    # TODO change the way to set spatial reference
    x1 = anchors[0][0]
    y1 = anchors[0][1]
    x2 = anchors[1][0]
    y2 = anchors[1][1]
    line = arcpy.Polyline(arcpy.Array([arcpy.Point(x1, y1), arcpy.Point(x2, y2)]), arcpy.SpatialReference(3400))
    try:
        # Buffer around line
        lineBuffer = arcpy.Buffer_analysis([line], arcpy.Geometry(), Line_Processing_Radius,
                                           "FULL", "ROUND", "NONE", "", "PLANAR")

        # Clip cost raster using buffer
        SearchBox = str(lineBuffer[0].extent.XMin) + " " + str(lineBuffer[0].extent.YMin) + " " + \
                    str(lineBuffer[0].extent.XMax) + " " + str(lineBuffer[0].extent.YMax)
        arcpy.Clip_management(Cost_Raster, SearchBox, fileClip, lineBuffer, "", "ClippingGeometry",
                              "NO_MAINTAIN_EXTENT")

        # Least cost path
        fileCostDist = CostDistance(arcpy.PointGeometry(arcpy.Point(x1, y1)), fileClip, "", fileCostBack)
        CostPathAsPolyline(arcpy.PointGeometry(arcpy.Point(x2, y2)), fileCostDist,
                           fileCostBack, fileCenterline, "BEST_SINGLE", "")

        # get centerline polyline out of memory feature class fileCenterline
        centerline = []
        with arcpy.da.SearchCursor(fileCenterline, ["SHAPE@"]) as cursor:
            for row in cursor:
                centerline.append(row[0])

    except Exception as e:
        print("Problem with line starting at X " + str(x1) + ", Y " + str(y1)
              + "; and ending at X " + str(x2) + ", Y " + str(y2) + ".")
        print(e)
        centerline = [None]
        return centerline

    # Clean temporary files
    arcpy.Delete_management(fileClip)
    arcpy.Delete_management(fileCostDist)
    arcpy.Delete_management(fileCostBack)

    return centerline


def workLinesMem(vertex):
    """
    New version of worklines. It uses memory workspace instead of shapefiles.
    The refactoring is to accelerate the processing speed.
        vertex: intersection with all lines crossed at the intersection
        return: one or two centerlines
    """

    # Temporary files
    outWorkspace = flmc.GetWorkspace(workspaceName)

    # read params from text file
    f = open(outWorkspace + "\\params.txt")
    Forest_Line_Feature_Class = f.readline().strip()
    Cost_Raster = f.readline().strip()
    Line_Processing_Radius = float(f.readline().strip())
    f.close()

    anchors = generateAnchorPairs(vertex)

    if not anchors:
        print("No anchors retrieved")
        return None

    centerline_1 = [None]
    centerline_2 = [None]
    intersection = None
    if len(anchors) == 4:
        centerline_1 = leastCostPath(Cost_Raster, anchors[0:2], Line_Processing_Radius)
        centerline_2 = leastCostPath(Cost_Raster, anchors[2:4], Line_Processing_Radius)

        if centerline_1 and centerline_2:
            intersection = intersectionOfLines(centerline_1, centerline_2)
    elif len(anchors) == 2:
        centerline_1 = leastCostPath(Cost_Raster, anchors, Line_Processing_Radius)

        if centerline_1:
            intersection = closestPointToLine(vertex["point"], centerline_1)

    # Update vertices according to intersection, new centerlines are returned
    temp = []
    # lines = updatePtInLines(vertex, intersection)
    temp.append(anchors)
    temp.append(centerline_1 + centerline_2)
    temp.append(intersection)
    temp.append(vertex)
    print("Processing vertex {} done".format(vertex["point"]))
    return temp


def main(argv=None):
    # Setup script path and workspace folder
    global workspaceName

    global outWorkspace
    outWorkspace = flmc.SetupWorkspace(workspaceName)
    arcpy.env.workspace = outWorkspace
    arcpy.env.overwriteOutput = True

    # Load arguments from file
    if argv:
        args = argv
    else:
        args = flmc.GetArgs("FLM_VO_params.txt")

    # Tool arguments
    global Forest_Line_Feature_Class
    Forest_Line_Feature_Class = args[0].rstrip()
    global Cost_Raster
    Cost_Raster = args[1].rstrip()
    global Line_Processing_Radius
    Line_Processing_Radius = args[2].rstrip()
    Out_Centerline = args[3].rstrip()

    # write params to text file
    f = open(outWorkspace + "\\params.txt", "w")
    f.write(Forest_Line_Feature_Class + "\n")
    f.write(Cost_Raster + "\n")
    f.write(Line_Processing_Radius + "\n")
    f.close()

    # Prepare input lines for multiprocessing
    desc = arcpy.Describe(Forest_Line_Feature_Class)
    oid = desc.oidFieldName
    flds = []
    for i in desc.fields:
        if i.type != "Geometry":  # Only attributes
            flds.append(i.name)

    segment_all = flmc.SplitLines(Forest_Line_Feature_Class, outWorkspace, "CL", False, KeepFieldName=flds)
    vertex_grp = groupIntersections(segment_all)

    pool = multiprocessing.Pool(processes=flmc.GetCores())
    flmc.log("Multiprocessing center lines...")
    flmc.log("Using {} CPU cores".format(flmc.GetCores()))
    centerlines = pool.map(workLinesMem, vertex_grp)
    pool.close()
    pool.join()
    flmc.logStep("Center line multiprocessing done.")

    # No line generated, exit
    if len(centerlines) <= 0:
        print("No lines generated, exit")
        return

    # Create output centerline shapefile
    flmc.log("Create centerline shapefile...")
    arcpy.CreateFeatureclass_management(os.path.dirname(Out_Centerline), os.path.basename(Out_Centerline),
                                        "POLYLINE", Forest_Line_Feature_Class, "DISABLED",
                                        "DISABLED", Forest_Line_Feature_Class)

    # write out new intersections
    file_name = os.path.splitext(Out_Centerline)

    file_leastcost = file_name[0] + "_leastcost" + file_name[1]
    arcpy.CreateFeatureclass_management(os.path.dirname(file_leastcost), os.path.basename(file_leastcost),
                                        "POLYLINE", "", "DISABLED", "DISABLED", Forest_Line_Feature_Class)

    file_anchors = file_name[0] + "_anchors" + file_name[1]
    arcpy.CreateFeatureclass_management(os.path.dirname(file_anchors), os.path.basename(file_anchors),
                                        "POINT", "", "DISABLED", "DISABLED", Forest_Line_Feature_Class)
    file_inter = file_name[0] + "_intersections" + file_name[1]
    arcpy.CreateFeatureclass_management(os.path.dirname(file_inter), os.path.basename(file_inter),
                                        "POINT", "", "DISABLED", "DISABLED", Forest_Line_Feature_Class)

    # Flatten centerlines which is a list of list
    flmc.log("Writing centerlines to shapefile...")
    anchor_list = []
    leastcost_list = []
    inter_list = []
    cl_list = []

    # Dump all polylines into point array for vertex updates
    ptarray_all = {}
    for i in segment_all:
        pt = []
        pt.append(i[0].getPart())
        pt.append(i[2])
        ptarray_all[i[1]] = pt

    for sublist in centerlines:
        if not sublist:
            continue
        if len(sublist) > 0:
            for pt in sublist[0]:
                anchor_list.append(pt)
            for line in sublist[1]:
                leastcost_list.append(line)

            inter_list.append(sublist[2])

            for line in sublist[3]["lines"]:
                index = line[1]
                pt_array = ptarray_all[line[3]["lineNo"]][0]
                ptarray_all.update({line[3]["lineNo"]: updatePtInLines(pt_array, index, sublist[2])})


    # arcpy.Merge_management(cl_list, Out_Centerline)
    # write all new intersections
    with arcpy.da.InsertCursor(file_anchors, ["SHAPE@"]) as cursor:
        for pt in anchor_list:
            if pt:
                cursor.insertRow([arcpy.Point(pt[0], pt[1])])

    with arcpy.da.InsertCursor(file_leastcost, ["SHAPE@"]) as cursor:
        for line in leastcost_list:
            if line:
                cursor.insertRow([line])

    # write all new intersections
    with arcpy.da.InsertCursor(file_inter, ["SHAPE@"]) as cursor:
        for pt in inter_list:
            if pt:
                cursor.insertRow([arcpy.Point(pt[0], pt[1])])

    with arcpy.da.InsertCursor(Out_Centerline, ["SHAPE@"]) as cursor:
        for line in ptarray_all.values:
            if line:
                row = [arcpy.Polyline(line[0])]
                for i in flds:
                    row.append(line[1][i])

                cursor.insertRow(row)

    # TODO: inspect CorridorTh
    if arcpy.Exists(Out_Centerline):
        arcpy.AddField_management(Out_Centerline, "CorridorTh", "DOUBLE")
        arcpy.CalculateField_management(Out_Centerline, "CorridorTh", "3")
    flmc.log("Centerline shapefile done")


if __name__ == '__main__':
    main()
