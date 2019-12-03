# Seismic Line Mapper (SLM)
## A tool for enhanced delineation and attribution of linear disturbances in forests

*Copyright (C) 2019  Applied Geospatial Research Group*

## Credits
This tool is part of the **Boreal Ecosystem Recovery and Assessment (BERA)** Project (http://www.beraproject.org/), and was developed by the **Applied Geospatial Research Group** (https://www.appliedgrg.ca/).

## Purpose / Description
SLM is a series of script tools for facilitating the high-resolution mapping and studying of seismic lines (petroleum exploration corridors in forested areas) via processing LiDAR-derived canopy height models. 
	
## Motivation
Given that the process of manually digitizing detailed small-scale (boreal) seismic lines is slow and prone to human error, a semi-automated solution is preferred for large-scale application areas.

## Development History
 - November, 2019: Workflow overhaul (least cost corridor & multiprocessing) by **Gustavo Lopes Queiroz**.
 - November, 2018: First version in Arcpy by **Silvia Losada**.
 - May, 2018: Initial concept (least cost path with ArcGIS model builder) by **Sarah Cole** and **Jerome Cranston**.

## Contact
Contact the Applied Geospatial Research Group (https://www.appliedgrg.ca/) at appliedgrg@gmail.com

## License
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

## How to use
Click "Clone or download" in the [Seismic Line Mapper Github page](https://github.com/appliedgrg/seismic-line-mapper) to access the latest version of the tool.

All SLM scripts require python 2.7 and ArcGIS 10 installed in order to run.

All python scripts in the root folder are associated to an Arc-Toolbox file (.TBX), in that same folder, which can be opened directly in ArcMap or ArcCatalog.

All "GUI" python scripts in the Multiprocessing folder can be opened directly (in file explorer) and require an ArcGIS license but do not require ArcGIS to be opened.

## Inputs
 1. Input raster: A high-resolution (pixel-size < 1m) canopy height model (CHM) raster image, preferably derived from high resolution LiDAR (>25 pts/m²), covering the area of interest.
 2. Input lines: A polyline feature class delineating the seismic lines in the area of interest, digitized at a large scale (1:5,000 to 1:20,000).
 3. Optional: Polygon feature class delineating important landscape features which are distinct in terms of forest structure (eg.: wetland classes inventory according to ABMI, https://abmi.ca/)

## Outputs
 1. Output lines: A detailed and corrected (according to the CHM) small scale version (approximately 1:1000) of the input seismic line feature class.
 2. Output polygons: A detailed areal footprint of the seismic lines in the form of small scale polygons (approximately 1:500).

## Limitations
 - This tool does not work automatically on completely (80% to 100%) regenerated seismic lines. 
> If a human interpreter is not able to see the footprint on the CHM it is likely that the SLM tool will also not be able to properly map it without fine-tuning. Regenerated seismic line segments can either be removed from the inputs or digitized on a smaller scale (adding more vertices, see step 3 in "Workflow").
 - The SLM tool was designed to work on seismic lines, which are usually narrow corridors (up to 15 meters wide). 
> SLM can also be used to map the footprint of wide linear features such as roads, pipelines and power-lines (up to 80 meters wide) but this requires fine-tuning the input parameters (usually with a larger corridor threshold, and sometimes including additional input lines to capture separate portions of the same feature).
 - The input lines and their vertices must be contained within the input raster and not overlap with null (no data) cells. 
> On the other hand, null cells are useful to represent unmapped regions and should be used (as opposed to extreme numeric values such as -9999 or +9999) especially in case there are "data holes" in the input raster.
 - Application areas with varying levels of tree density may require additional care.
> Landscape feature polygons (optional input listed above) may be used to split seismic lines via the included "Split by Polygon" tool, enabling improved results on terrain with varying tree density. The included "Zonal Threshold" tool can help with  fine tuning individual line corridor thresholds (see step 5 in "Workflow" below) to prevent the footprint polygons from invading the surrounding forest in sparsely vegetated areas.
 - Water bodies (e.g.: rivers, ponds, lakes), cut-blocks and wide linear disturbances (e.g.: roads, pipelines) represent areas with extremely low tree density and may be confused as seismic line footprint. 
> Therefore, to avoid this effect, seismic lines surrounding these features may have to be digitized on a smaller scale (1:2000), with more vertices than other input lines (see step 3 in "Workflow" below).	
 - The least-cost path solution incorporated in this tool may occasionally choose to "cut-corners" on windy seismic lines with sparcely vegetated surroundings.
> This effect is worse if the input lines are too large-scale (e.g.: 1:20,000). To avoid this issue such corners may have to be enforced with additional vertices (see step 3 in "Workflow" below). Note that this effect is expected to be minimal, and may not be reflected in the output polygons even though output lines are affected.

## Workflow
 - Step 1: Prepare input raster layers. 
	 - Using the CHM raster as input, run the **Canopy Raster** tool, then the **Cost Raster** tool.
 - Step 2: Prepare input lines.
	 - Digitize large scale (1:5,000 to 1:20,000) input lines. Preferably use the Cost Raster generated on step one as reference. Then, run the **Center Line** tool.
 - Step 3: Inspect center lines. 
	 - Local canopy gaps, anomalies, and misplaced input lines may cause undesired deviations in the output center lines. If the center lines are appropriate upon inspection, move to Step 4. Otherwise correct the imperfect input lines, adding vertices on a smaller scale (1:2,000) to better guide the center lines towards the actual seismic line path, then re-run the **Center Line** tool. It is expected that, following the recomendations listed in the "Limitations" section above, only minor corrections will be needed in this step.
 - Step 4: Set up the least cost corridor threshold (LCCT). 
	 - The LCCT parameter will determine how wide the footprint is and how far it can penetrate in the adjacent forest. If the forest composition is approximately homogeneous in the application area, then all lines may use the same value for the LCCT (default is 8.0). Otherwise, the center lines will need to be attributed individually with appropriate corridor thresholds. This attribution can be done automatically using the **Zonal Threshold** tool. For improved threshold estimation, first the lines may be segmented according to input landscape feature polygons using the **Split by Polygon** tool. When the LCCT has been set up for all lines run the **footprint solution***.
 - Step 5: Inspect footprint polygons. 
	 - Adjust LCCT of line segments as needed. Wide lines may need a threshold increase while narrow lines on sparcely vegetated terrain may need a decrease. This can be done manually for each line or automatically by fine-tuning the parameters of the **Zonal Threshold** tool. Certain segments may transition between forest types not captured in the input landscape features and may have to be segmented. Re-run the **footprint solution*** until results are satisfactory.
	
**Footprint solution***: There are two ways to generate the footprint layer. The **Line Footprint** tool will directly generate the footprint, while the **Corridor** tool will generate an intermediate corridor raster layer then the **Corridor Footprint** tool will use the intermediate corridor layer to generate the footprint. The advantage of using intermediate steps is to quickly investigate the appropriate LCCT directly on the corridor raster.
		
## Multiprocessing
On large application areas (more than 4 lines or 20 km of cumulative length) it is strongly advised that the multiprocessing tools (included in the "Multiprocessing" folder) are used instead of the traditional ArcToolbox tools. 

Multiprocessing scripts can make use of multiple CPU cores to process multiple lines at once via parallel processing. While the single-processing SLM scripts can take "days" to process large areas, the multi-processing SLM scripts can process those same areas in the order of minutes.

While running the multiprocessing tools make sure that files in the output folders are not opened in ArcGIS, as this will place a "lock" in the files preventing them from being edited. To make sure that there are no locks affecting the tools, clean the output folders before running any tools.
	
## Future development
 - Object attribution: We intend to add attribution functionalities to the SLM, with the aim of aiding ecology studies and recovery assessments looking at seismic lines.
