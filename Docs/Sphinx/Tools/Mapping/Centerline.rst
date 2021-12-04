*******************
Centerline
*******************

Determines the least cost path between vertices of the input lines.

Python Interface
================


Method
-----------
Centerline provide Python method for calling directly:

.. code-block::

    def centerline(in_line, in_cost_raster, out_center_line,
                   line_radius=35, process_segments=True)

Parameters
-----------
* **in_line**:	Input polyline shapefile.	
* **in_cost_raster**:	Input raster image used to calculate the least cost path.	
* **line_radius**	Maximum processing distance from input lines. A large search radius may increase processing times whereas a small radius may cause undesired clipping.
* **process_segments**:	If set to True, will process each segment between each vertex of the input lines separately. If set to False, will process each line from start to end ignoring midpoints. The default is True, since it is assumed that the input lines for this tool are lines manually digitized at regional-scale with sparse vertices at a fine-scale. If using fine-scale (1:1,000) lines as input this may be set to False.
* **out_center_line**:	Output center-line shapefile.

Notes
=============