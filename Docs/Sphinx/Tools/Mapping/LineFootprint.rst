*******************
Footprint
*******************

Creates footprint polygons for each input line based on a least cost corridor method and individual line thresholds.

Python Interface
================


Method
-----------
Footprint provide Python method for calling directly:

.. code-block::

    def lineFootprint(in_center_line, in_canopy_raster, in_cost_raster, out_footprint,
                      corridor_thresh="CorridorTh", max_line_width=10,
                      expand_shrink_range=0, process_segments=False):

Parameters
-----------
* **Center-lines Feature Class**:	Input polyline shapefile.
* **Canopy Raster**:	Input raster image used to exclude canopy from line footprint.	
* **Cost Raster**:	Input raster image used to calculate the least cost corridor.	
* **Corridor Threshold Field**:	Name of the field (within the input lines) that indicates the least cost corridor thresholds (LCCT).
* **Maximum Line Width**:	Maximum processing width for input lines. A large value may increase processing times whereas a small value may cause undesired clipping.
* **Expand And Shrink Cell Range**:	Range used for cell erosion before final polygons are generated. Useful to remove small artifacts. If the cell size is 1m or larger then set this as zero.
* **Process Segments**:	If set to False, will process each line from start to end ignoring midpoints. If set to True, will process each segment between each vertex of the input lines separately. The default is False, since it is assumed that the input lines for this tool are manually corrected center-lines. If using regional-scale (1:20,000) lines as input this may be set to True.
* **Output Shapefile**:	Output footprint polygons.


Notes
=============