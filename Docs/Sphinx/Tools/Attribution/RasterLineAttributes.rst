**********************
Raster Line Attributes
**********************

Samples a raster image along lines and assigns cell statistics to each line.

Python Interface
================


Method
-----------
Raster Line Attributes provide Python method for calling directly:

.. code-block::
  
   def rasterAttribute(sampling_type, in_line, in_footprint, in_chm, out_line_attribute,
                       segment_lenght=30, line_split_tolerance=3, max_line_width=25):

Parameters
-----------
* **Input Lines**:	Input forest line center shapefile which will be segmented and attributed.
* **Input Raster Variable**:	Input raster image that will be sampled to attribute the input lines.
* **Sampling Type**:	How the input lines are segmented for attribution:
 * **IN-FEATURES**, the input features are attributed without subdivisions; 
 * **WHOLE-LINE**, the entire extent of each line is attributed without subdivisions; 
 * **LINE-CROSSINGS**, each line is split at line intersections; ARBITRARY, each line is segmented using an arbitrary length.
* **Sampling Interval**: Sampling interval along input lines in meters.
* **Segment Length**:	Arbitrary segment length (m). If the Sampling Type field is not set as ARBITRARY this field is ignored.
* **Line Split Tolerance**:	Tolerance radius (m) used to split lines. If the Sampling Type field is set as WHOLE-LINE this field is ignored.
* **Sampling Method	Method**: used to handle samples when attributing lines: Minimum, Maximum, Mean, Standard Deviation, Median, Mode, or Range.
* **Output Attributed Segments**:	Output features that will be created.


Notes
=============