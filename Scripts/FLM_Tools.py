import inspect
import os
import sys


currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

def canopyCost(in_raster,
               output_canopy_raster, output_cost_raster,
               height_thresh=1, search_radius=3,
               max_line_dist=10, canopy_avoidance=0.3,
               cost_exponent=1.5):
    """
    Generate cost raster
    """
    import FLM_CanopyCost

    print("Processing canopy cost: ", output_canopy_raster)
    argv = [None] * 8
    argv[0] = in_raster  # CHM raster
    argv[1] = height_thresh  # Canopy Height Threshold
    argv[2] = search_radius  # Tree Search Radius
    argv[3] = max_line_dist  # Maximum Line Distance
    argv[4] = canopy_avoidance  # Canopy Avoidance
    argv[5] = cost_exponent  # Cost Raster Exponent
    argv[6] = output_canopy_raster  # Output Canopy Raster
    argv[7] = output_cost_raster  # Output Cost Raster
    print(argv[6])

    if not os.path.exists(output_canopy_raster) and not os.path.exists(output_cost_raster):
        FLM_CanopyCost.main(argv)


def centerline(in_line, in_cost_raster, out_center_line,
               line_radius=35, process_segments=True):
    """
    Generate centerline
    """

    import FLM_CenterLine

    print("Processing center line: ", out_center_line)
    argv = [None] * 5
    argv[0] = in_line  # input line
    argv[1] = in_cost_raster  # Cost raster
    argv[2] = line_radius  # line process radius
    argv[3] = process_segments  # Process segments
    argv[4] = out_center_line  # Output center line

    if not os.path.exists(output_center_line):
        FLM_CenterLine.main(argv)


def lineFootprint(in_center_line, in_canopy_raster, in_cost_raster,
                   out_footprint,
                   corridor_thresh="CorridorTh", max_line_width=10,
                   expand_shrink_range=0, process_segments=False):
    """
    Generate line footprint
    """
    import FLM_LineFootprint

    print("Processing canopy line footprint: ", out_footprint)
    argv = [None] * 8
    argv[0] = in_center_line  # center line
    argv[1] = in_canopy_raster  # canopy raster
    argv[2] = in_cost_raster  # Cost raster
    argv[3] = corridor_thresh  # corridor threshold field
    argv[4] = str(max_line_width)  # maximam line width
    argv[5] = str(expand_shrink_range)  # expand and shrink cell range
    argv[6] = str(process_segments)  # process segments
    argv[7] = out_footprint  # Output line foot print

    if os.path.exists(in_center_line) and not os.path.exists(out_footprint):
        FLM_LineFootprint.main(argv)


def lineAttribute(mode, in_line, in_footprint, in_chm, out_line_attribute,
                  segment_lenght=30, line_split_tolerance=3, max_line_width=25):
    """
    Generate line attribute
    mode: IN_FEATURES, WHOLE_LINE, LINE_CROSSINGS, ARBITRARY
    """
    import FLM_ForestLineAttributes

    print("Processing forest line attributes {0} under mode {1}".format(out_line_attribute, mode))
    argv = [None] * 8
    argv[0] = in_line # input line (output)
    argv[1] = in_footprint  # line footprint
    argv[2] = in_chm  # input CHM
    argv[3] = mode    # sampling type
    argv[4] = str(segment_lenght)  # Segment length
    argv[5] = str(line_split_tolerance)  # line split tolerance
    argv[6] = str(max_line_width)  # maximum line width
    argv[7] = out_line_attribute   # Output line attributes

    if os.path.exists(in_line) and not os.path.exists(out_line_attribute):
        FLM_ForestLineAttributes.main(argv)

def rasterAttribute(self):
    return
