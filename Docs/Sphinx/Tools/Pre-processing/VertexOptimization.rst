*******************
Vertex Optimization
*******************

Relocating line intersections to seismic line paths

Python Interface
================


Method
-----------
Vertex Optimization provide Python method for calling directly:
.. code-block:: python
    def vertexOptimization(in_line, in_cost_raster, out_center_line, line_radius=35)

Parameters
-----------
* **Forest Lines Feature Class**:	Input polyline shapefile.
* **Cost Raster	Input**: Raster image used to calculate the least cost path.
* **Output Center-Line**:	Output optimized center-line shapefile.

Notes
=============