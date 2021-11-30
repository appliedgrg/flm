*************
Pre-tagging
*************

Tagging lines by examining lines existence in CHM rasters

Python Interface
================


Method
-----------
Pre-tagging provide Python method for calling directly:
.. code-block:: python
    def preTagging(in_center_line, in_chm, in_canopy_raster, in_cost_raster, in_lidar_year,
                   out_tagged_line, corridor_thresh="CorridorTh", max_line_width=10,
                   process_segments=False):

Parameters
-----------
* **Input Lines**:	Input forest line center shapefile which will be segmented and attributed.

* **Canopy Height Model (CHM) Raster**:	Input CHM raster file used as basis for mapping forest lines and their footprint. This layer should be projected in any Universal Transverse Mercator (UTM) coordinate system. The data should be preferably derived from high resolution LiDAR or photogrammetry (>25 pts/m²).

* **Canopy Raster**:	Input raster image used to exclude canopy from line footprint.	

* **Cost Raster**:	Input raster image used to calculate the cost corridor.

* **Input LiDAR Coverage with Year**:	Polygons of different LiDAR sources coverage with acquisition year.

* **Output Tagged Line**:	Output features that will be tagged.

Algorithm
----------
.. figure:: ../../flowchart_pre-tagging.png
   :align: center

Notes
=============