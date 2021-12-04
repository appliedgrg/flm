*******************
Canopy Cost Raster
*******************

Creates a canopy raster and a cost raster from a CHM input raster. The output rasters are used for subsequent FLM tools.

Python Interface
================


Method
-----------
Canopy Cost Raster provide Python method for calling directly:

.. code-block:: python 
    
    def canopyCost(in_raster,
                   out_canopy_raster, out_cost_raster,
                   height_thresh=1, search_radius=3,
                   max_line_dist=10, canopy_avoidance=0.3,
                   cost_exponent=1.5):

Parameters
-----------
* **in_raster**:	Input forest line center shapefile which will be segmented and attributed.

* **Canopy Height Model (CHM) Raster**:	Input CHM raster file used as basis for mapping forest lines and their footprint. This layer should be projected in any Universal Transverse Mercator (UTM) coordinate system. The data should be preferably derived from high resolution LiDAR or photogrammetry (>25 pts/m²).
* **height_thresh**:	Height threshold in meters above which CHM pixels are considered canopy.
* **search_radius**:	Radius of canopy influence in the cost raster. This factor smooths the canopy in the cost raster which helps to prevent gaps in sparsely vegetated areas (e.g. wetlands) to be incorrectly identified as footprint. A large search radius (>=5m) may cause excessive smoothing of the cost raster which can lead to least cost paths ignoring forest-line nuances in sparsely vegetated forests. A small radius (<=1m) may cause the least cost path to cut corners through small gaps in sparse vegetation as well as avoid small obstacles that should not affect overall line shape.
* **max_line_dist**:	Maximum euclidean distance from canopy. This is a second smoothing factor which helps to position the forest line shape in the center of the line footprint. An excessively small (<=1m) or large (>20m) value may cause the center line to be positioned close to one of the edges of the footprint.
* **canopy_avoidance**:	Ratio of importance between canopy search radius and euclidean distance. A value close to zero (0) prioritizes search radius whereas a value close to one (1) prioritizes euclidean distance. A small value (<=0.1) may cause the forest lines to miss nuances in sparsely vegetated terrain whereas a big value (>=0.5) may overemphasize turns in complex trails. This factor influences final footprint size in a minor way.
* **cost_exponent**:	Affects the cost of vegetated areas in an exponential fashion. A low (<=1) exponent may lead to lines cutting through corners, whereas a large (>=3) exponent may lead to least cost paths completely avoiding narrow lines.
* **out_canopy_raster**:	Output raster classified as canopy (1) and non-canopy (0).	
* **out_cost_raster**:	Output cost raster used in subsequent FLM tools for least-cost analysis.

Notes
=============