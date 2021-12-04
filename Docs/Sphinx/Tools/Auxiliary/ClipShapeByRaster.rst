*********************
Clip Shape By Raster
*********************

Extracts input features that overlay raster cells which are not NoData. This is useful to prepare input forest lines for corridor analysis, since vertices must overlap with valid cells for least cost methods.

Python Interface
================


Method
-----------
Clip Shape By Raster provide Python method for calling directly:

.. code-block:: Python
   
   def clipShapeByRaster(in_line, clip_raster, shrink_size, out_line)

Parameters
-----------
* **in_line**	Input features to be clipped.	
* **clip_raster**	Input raster used to clip the input features.	
* **shrink_size**	Number of cells to shrink in order to avoid raster edge contact.
* **out_line**	Output features that will be created.


Notes
=============