*******************
Zonal Threshold
*******************

Assigns corridor thresholds to the input lines based on their surrounding canopy density.

Python Interface
================


Method
-----------
Zonal Threshold provide Python method for calling directly:

.. code-block::

    def zonalThreshold(in_line, corridor_thresh, canopy_raster, canopy_search_radius
                       min_value, max_value, out_line)

Parameters
-----------
* **Input Lines**:	Input polyline shapefile for which each feature will be assigned an unique corridor threshold.
* **corridor_thresh**:	Name of the field (within the input lines) that indicates the corridor thresholds.
* **canopy_raster**:	Input canopy raster used to estimate canopy density.
* **canopy_search_radius**:	Search radius around line features where zonal statistics are calculated.
* **min_value**:	Minimum value for corridor threshold.
* **max_value**:	Maximum value for corridor threshold.
* **out_line**:	Output features that will be created.

Notes
=============