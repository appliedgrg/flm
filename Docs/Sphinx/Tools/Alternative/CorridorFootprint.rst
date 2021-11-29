*******************
Corridor Footprint
*******************

Creates footprint polygons for each input line based on a least cost corridor raster and individual line thresholds. This step can be skipped with the 'Line Footprint' tool.

Python Interface
================


Method
-----------
Corridor Footprint provide Python method for calling directly:
.. code-block:: python
    def corridorFootprint(in_line, in_canopy_raster, in_corridor_raster, corridor_thresh, max_line_width, expand_shrink_range, out_footprint)

Parameters
-----------
* **in_line**:	Input polyline shapefile.
* **in_canopy_raster**:	Input raster image used to exclude canopy from line footprint.
* **in_corridor_raster**:	Input corridor raster image where a threshold is applied to generate footprints.
* **corridor_thresh**:	Name of the field (within the input lines) that indicates the least cost corridor thresholds (LCCT).
* **max_line_width**:	Maximum processing width for input lines. A large value may increase processing times whereas a small value may cause undesired clipping.
* **expand_shrink_range**:	Range used for cell erosion before final polygons are generated. Useful to remove small artifacts. If the cell size is 1m or larger then set this as zero.
* **out_footprint**:	Output footprint polygons.

Notes
=============