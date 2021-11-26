import arcpy

class Toolbox(object):
    def __init__(self):
        self.label =  "Forest Line Mapper"
        self.alias  = "FLM"

        # List of tool classes associated with this toolbox
        self.tools = [Centerline] 

class Centerline(object):
    def __init__(self):
        self.label       = "Center Line"
        self.description = "Determines the least cost path between vertices of the input lines."

    def getParameterInfo(self):
        # Define parameter definitions

        # Input Features parameter
        in_line_features = arcpy.Parameter(
            displayName="Input Forest Line Feature Class",
            name="in_line_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        in_line_features.filter.list = ["Polyline"]

        in_cost_raster = arcpy.Parameter(
            displayName="Input Cost Raster",
            name="in_cost_raster",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")
        
        # Line processing radius parameter
        line_processing_radius = arcpy.Parameter(
            displayName="Line Processing Radius",
            name="line_processing_radius",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        
        line_processing_radius.value = 20

        # Process segments parameter
        process_segments = arcpy.Parameter(
            displayName="Process Segments",
            name="process_segments",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        
        process_segments.value = False
        
        # Derived Output Features parameter
        out_centerline = arcpy.Parameter(
            displayName="Output Center Line",
            name="out_centerline",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")
        
        parameters = [in_line_features, in_cost_raster, line_processing_radius, process_segments, out_centerline]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        inLineFeatures  = parameters[0].valueAsText
        inCostRaster  = parameters[1].valueAsText
        lineProcessingRadius  = parameters[2].valueAsText
        prpcessSegments   = parameters[3].valueAsText
        outCenterline = parameters[4].valueAsText
        
        print(inLineFeatures, inCostRaster, lineProcessingRadius, prpcessSegments, outCenterline)