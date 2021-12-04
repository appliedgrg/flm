*******************
Corridor Raster
*******************

Creates a least cost corridor raster between vertices of the input lines. This step can be skipped with the 'Line Footprint' tool.

Python Interface
================


Method
-----------
Corridor Raster provide Python method for calling directly:

.. code-block:: python

    def corridorRaster(in_line, in_canopy_raster, in_cost_raster, max_line_width, process_segment, out_raster)

Parameters
-----------
* **in_line**:	Input polyline shapefile.	
* **in_canopy_raster**:	Input raster image used to exclude canopy from line footprint.	
* **in_cost_raster**:	Input raster image used to calculate the cost corridor.	
* **max_line_width**:	Maximum processing width for each line. A large value may increase processing times whereas a small value may cause undesired clipping.
* **process_segment**:	If set to False, will process each line from start to end ignoring midpoints, if set to True, will process each segment between each vertex of the input lines separately. The default is False, since it is assumed that the user will manually correct centerlines before running this tool.
* **out_raster**:	Output corridor raster name.

Notes
=============