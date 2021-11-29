*********************
Forest Line Atributes
*********************

Calculates a series of attributes related to forest line shape, size and microtopography. Line-derived attributes include: length, bearing, orientation and sinuosity; Polygon-derived attributes include: area, average width, perimeter and perimeter-area ratio; CHM-derived attributes include: average vegetation height, vegetation volume and vegetation roughness.

Python Interface
================


Method
-----------
Forest Line Atributes provide Python method for calling directly:
.. code-block:: python
    def lineAttribute(sampling_type, in_line, in_footprint, in_chm, out_line_attribute,
                      segment_lenght=30, line_split_tolerance=3, max_line_width=25):

Parameters
-----------

* **Input Lines**:	Input forest line center shapefile which will be segmented and attributed.	

* **Input Footprint Polygons**:	Input forest line footprint shapefile used to derive spatial attributes.	
* **Input Raster CHM**:	Input canopy height model raster used to derive microtopography attributes.	
* **Sampling Type**:	How the input lines are segmented for attribution:   
 * **IN-FEATURES**, the input features are attributed without subdivisions; 
 * **WHOLE-LINE**, the entire extent of each line is attributed without subdivisions;
 * **LINE-CROSSINGS**, each line is split at line intersections;
 * **ARBITRARY**, each line is segmented using an arbitrary length.
* **Segment Length**:	Arbitrary segment length (m). If the Sampling Type field is not set as ARBITRARY this field is ignored.
* **Line Split Tolerance**:	Tolerance radius (m) used to split lines. If the Sampling Type field is set as WHOLE-LINE this field is ignored.
* **Maximum Line Width**:	Maximum line width (m) used to search for surrounding footprint.
* **Output Attributed Segments**:	Output features that will be created.


Notes
=============