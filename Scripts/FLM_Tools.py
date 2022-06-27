import inspect
import os
import sys

# local imports
import FLM_CanopyCost
import FLM_Pretagging
import FLM_VertexOptimization
import FLM_CenterLine
import FLM_LineFootprint
import FLM_ForestLineAttributes

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

def canopyCost(in_raster,
               out_canopy_raster, out_cost_raster,
               height_thresh=1, search_radius=3,
               max_line_dist=10, canopy_avoidance=0.3,
               cost_exponent=1.5):
    """
    Generate cost raster
    """
    print("Processing canopy cost: ", out_canopy_raster)
    argv = [None] * 8
    argv[0] = in_raster  # CHM raster
    argv[1] = str(height_thresh)  # Canopy Height Threshold
    argv[2] = str(search_radius)  # Tree Search Radius
    argv[3] = str(max_line_dist)  # Maximum Line Distance
    argv[4] = str(canopy_avoidance)  # Canopy Avoidance
    argv[5] = str(cost_exponent)  # Cost Raster Exponent
    argv[6] = out_canopy_raster  # Output Canopy Raster
    argv[7] = out_cost_raster  # Output Cost Raster
    print(argv[6])

    if not os.path.exists(out_canopy_raster) and not os.path.exists(out_cost_raster):
        FLM_CanopyCost.main(argv)


def preTagging(in_center_line, in_chm, in_canopy_raster, in_cost_raster, in_lidar_year,
               out_tagged_line, corridor_thresh="CorridorTh", max_line_width=32):
    """
    Generate line footprint
    """

    print("Tagging lines: ", out_tagged_line)
    argv = [None] * 9
    argv[0] = in_center_line  # center line
    argv[1] = in_chm
    argv[2] = in_canopy_raster  # canopy raster
    argv[3] = in_cost_raster  # Cost raster
    argv[4] = in_lidar_year  # Input LiDAR coverage with acquisition year
    argv[5] = str(max_line_width)  # maximam line width
    argv[6] = out_tagged_line  # Output line foot print

    if not os.path.exists(in_center_line):
        print("Input line file {} not exists, ignore.".format(in_center_line))
        return

    if os.path.exists(out_tagged_line):
        print("Footprint file {} already exists, ignore.".format(out_tagged_line))
        return

    FLM_Pretagging.main(argv)


def vertexOptimization(in_line, in_cost_raster, out_center_line, line_process_radius=35):
    """
    Optimize vertices
    """

    print("Processing center line: ", out_center_line)
    argv = [None] * 4
    argv[0] = in_line  # input line
    argv[1] = in_cost_raster  # Cost raster
    argv[2] = str(line_process_radius)  # line process radius
    argv[3] = out_center_line  # Output center line

    if not os.path.exists(in_line):
        print("Input line file {} not exists, ignore.".format(in_line))
        return

    if os.path.exists(out_center_line):
        print("Centeline file {} already exists, ignore.".format(out_center_line))
        return

    FLM_VertexOptimization.main(argv)


def centerline(in_line, in_cost_raster, out_center_line,
               line_radius=35, process_segments=True):
    """
    Generate centerline
    """

    print("Processing center line: ", out_center_line)
    argv = [None] * 5
    argv[0] = in_line  # input line
    argv[1] = in_cost_raster  # Cost raster
    argv[2] = str(line_radius)  # line process radius
    argv[3] = str(process_segments)  # Process segments TODO: bool or sting?
    argv[4] = out_center_line  # Output center line

    if not os.path.exists(in_line):
        print("Input line file {} not exists, ignore.".format(in_line))
        return

    if os.path.exists(out_center_line):
        print("Centeline file {} already exists, ignore.".format(out_center_line))
        return

    FLM_CenterLine.main(argv)


def lineFootprint(in_center_line, in_canopy_raster, in_cost_raster,
                   out_footprint,
                   corridor_thresh="CorridorTh", max_line_width=10,
                   expand_shrink_range=0, process_segments=False,
                   corridor_threshold=3):
    """
    Generate line footprint

    """

    print("Processing canopy line footprint: ", out_footprint)
    argv = [None] * 9
    argv[0] = in_center_line  # center line
    argv[1] = in_canopy_raster  # canopy raster
    argv[2] = in_cost_raster  # Cost raster
    argv[3] = corridor_thresh  # corridor threshold field
    argv[4] = str(corridor_threshold)
    argv[5] = str(max_line_width)  # maximam line width
    argv[6] = str(expand_shrink_range)  # expand and shrink cell range
    argv[7] = str(process_segments)  # process segments
    argv[8] = out_footprint  # Output line foot print

    if not os.path.exists(in_center_line):
        print("Input line file {} not exists, ignore.".format(in_center_line))
        return

    if os.path.exists(out_footprint):
        print("Footprint file {} already exists, ignore.".format(out_footprint))
        return

    FLM_LineFootprint.main(argv)


def lineAttribute(sampling_type, in_line, in_footprint, in_chm, out_line_attribute,
                  segment_lenght=30, line_split_tolerance=3, max_line_width=25):
    """
    Generate line attribute
    sampling_type: IN-FEATURES, WHOLE-LINE, LINE-CROSSINGS, ARBITRARY
    """

    print("Processing forest line attributes {0} under mode {1}".format(out_line_attribute, sampling_type))
    argv = [None] * 8
    argv[0] = in_line  # input line (output)
    argv[1] = in_footprint  # line footprint
    argv[2] = in_chm  # input CHM
    argv[3] = sampling_type    # sampling type
    argv[4] = str(segment_lenght)  # Segment length
    argv[5] = str(line_split_tolerance)  # line split tolerance
    argv[6] = str(max_line_width)  # maximum line width
    argv[7] = out_line_attribute   # Output line attributes

    if not os.path.exists(in_line):
        print("Input line file {} not exists, ignore.".format(in_line))
        return

    if os.path.exists(out_line_attribute):
        print("Attribute file {} already exists, ignore.".format(out_line_attribute))
        return

    FLM_ForestLineAttributes.main(argv)

def rasterAttribute(self):
    return

def FLM_DynamicCanopyThreshold(cl_fc,chm,process_segments,Search_R, Canopy_Percentile,CanopyTh_Percent,
                             TreeSearchRadius,MaximumLineDistance,  CanopyAvoidance,CostRasterExponent):
    """
       Generate line attribute
       sampling_type: IN-FEATURES, WHOLE-LINE, LINE-CROSSINGS, ARBITRARY
       """

    print("Processing dynamic footprint")
    try:
        argv = [None] * 10
        argv[0] = cl_fc  # input line (output)
        argv[1] = chm  # CHM raster
        argv[2] = str(process_segments)  # process segments
        argv[3] = str(Search_R)  # Offset line distance
        argv[4] = str(Canopy_Percentile)  # Canopy Nth Percentile
        argv[5] = str(CanopyTh_Percent) # Canopy Threshold Percentage
        argv[6] = str(TreeSearchRadius)  # Tree Search Radius
        argv[7] = str(MaximumLineDistance)  # Maximum Line Distance
        argv[8] = str(CanopyAvoidance)  # Canopy Avoidance
        argv[9] = str(CostRasterExponent)  # Cost Raster Exponent

    except Exception as e:
        print("Error: Please Check the input.")
        print(e)
        sys.exit()


    if not os.path.exists(cl_fc):
        print("Input line file {} not exists, ignore.".format(cl_fc))
        return

    FLM_DynamicCanopyThreshold.main(argv)

def FLM_DynamicLineFootprint(cl_fc,chm,max_line_width,expand_shrink_range,process_segments,out_footprint,
                             TreeSearchRadius,MaximumLineDistance, CanopyAvoidance,CostRasterExponent):
    """
       Generate line attribute
       sampling_type: IN-FEATURES, WHOLE-LINE, LINE-CROSSINGS, ARBITRARY
       """

    print("Processing dynamic footprint")
    try:
        argv = [None] * 10
        argv[0] = cl_fc  # input line (output)
        argv[1] = chm  # CHM raster
        argv[2] = str(max_line_width)  # maximam line width
        argv[3] = str(expand_shrink_range)  # expand and shrink cell range
        argv[4] = str(process_segments)  # process segments
        argv[5] = out_footprint  # Output line foot print
        argv[6] = str(TreeSearchRadius)  # Tree Search Radius
        argv[7] = str(MaximumLineDistance)  # Maximum Line Distance
        argv[8] = str(CanopyAvoidance)  # Canopy Avoidance
        argv[9] = str(CostRasterExponent)  # Cost Raster Exponent
    except Exception as e:
        print("Error: Please Check the input.")
        print(e)
        sys.exit()


    if not os.path.exists(cl_fc):
        print("Input line file {} not exists, ignore.".format(cl_fc))
        return

    FLM_DynamicLineFootprint.main(argv)

def FLM_DynamicLineFootprintFullStep(cl_fc,chm,max_line_width,expand_shrink_range,process_segments,Search_R,out_footprint,
                             Canopy_Percentile,CanopyTh_Percent,TreeSearchRadius,MaximumLineDistance,
                             CanopyAvoidance,CostRasterExponent):
    """
       Generate line attribute
       sampling_type: IN-FEATURES, WHOLE-LINE, LINE-CROSSINGS, ARBITRARY
       """

    print("Processing dynamic footprint")
    try:
        argv = [None] * 13
        argv[0] = cl_fc  # input line (output)
        argv[1] = chm  # CHM raster
        argv[2] = str(max_line_width)  # maximam line width
        argv[3] = str(expand_shrink_range)  # expand and shrink cell range
        argv[4] = str(process_segments)  # process segments
        argv[5] = out_footprint  # Output line foot print
        argv[6] = str(Search_R)  # Offset line distance
        argv[7] = str(Canopy_Percentile)  # Canopy Nth Percentile
        argv[8] = str(CanopyTh_Percent) # Canopy Threshold Percentage
        argv[9] = str(TreeSearchRadius)  # Tree Search Radius
        argv[10] = str(MaximumLineDistance)  # Maximum Line Distance
        argv[11] = str(CanopyAvoidance)  # Canopy Avoidance
        argv[12] = str(CostRasterExponent)  # Cost Raster Exponent
    except Exception as e:
        print("Error: Please Check the input.")
        print(e)
        sys.exit()


    if not os.path.exists(cl_fc):
        print("Input line file {} not exists, ignore.".format(cl_fc))
        return

    FLM_DynamicLineFootprintFullStep.main(argv)
