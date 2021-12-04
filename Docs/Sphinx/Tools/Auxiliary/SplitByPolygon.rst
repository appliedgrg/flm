*******************
Split By Polygon
*******************

Splits the input lines where they intersect the edges of the input polygons.

Python Interface
================


Method
-----------
Split By Polygon provide Python method for calling directly:

.. code-block::
  
   def splitByPolygon(in_line, split_polygon, out_line)

Parameters
-----------
* **in_line**:	Input polyline shapefile to be split.	
* **split_polygon**:	Input polygon shapefile that is used to split the input lines.	
* **out_line**:	Output features that will be created.

Notes
=============