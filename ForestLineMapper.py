# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Forest line Mapper
# Date: 2020-Jan-22
#
# Development history:
#   Switch massive file cache to memory workspace and geometries.
#   Eliminate frequent file I/O line setup process and switch geoprocessing
#   tools to memory-based approach. 2021, Richard Zeng
#
#   Worflow overhaul by Gustavo Lopes Queiroz, November, 2019
#   First version in Arcpy by Silvia Losada, November 2018
#   Initial concept by Sarah Cole and Jerome Cranston, May 2018
#   
# Citation: Applied Geospatial Research Group, 2020. Forest Line Mapper: 
# A tool for enhanced delineation and attribution of linear disturbances in 
# forests.
#
# FLM is a series of script tools for facilitating the high-resolution mapping 
# and studying of forest lines (petroleum exploration corridors in forested 
# areas) via processing canopy height models (LiDAR or photogrammetry derived 
# raster images where pixel-values represent the ground-height of vegetation).
#
# Usage: Follow the instructions available in the FLM webpage.
# Webpage: https://github.com/appliedgrg/flm
#
# ---------------------------------------------------------------------------
#
#    Copyright (C) 2021  Applied Geospatial Research Group
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://gnu.org/licenses/gpl-3.0>.
#
# ---------------------------------------------------------------------------
#
# ForestLineMapper.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: This script contains the tool names, parameters and decriptions.
# GUI is constructed based on calls contained within this script. 
#
# ---------------------------------------------------------------------------
# System imports
import os
import sys
import json

# Local imports
# add scriptPath to sys.path
scriptPath = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(scriptPath, "Scripts"))
import FLM_Common as flmc
import FLM_GUI_Tools as gui

version = ""


class FLMToolDialogue:
    def __init__(self, title, description, fields, types, tips, defaults, scriptFile, paramPath):
        self.title = title
        self.description = description
        self.fields = fields
        self.types = types
        self.tips = tips
        self.defaults = defaults
        self.scriptFile = scriptFile
        self.paramPath = paramPath
        self.input = []
        self.toolScreen = None

    def SetupTool(self, toolScreen):
        self.toolScreen = toolScreen
        entries = gui.ToolSetup(toolScreen, self.title, self.description, self.fields,
                                self.types, self.tips, self.scriptFile, self.paramPath)
        self.input = entries
        self.LoadParams()

    def OpenTool(self):
        gui.OpenScreen(self, self.toolScreen)

    def SaveParams(self):
        pfile = open(self.paramPath, "w")
        for i in range(0, len(self.input)):
            pfile.write(self.input[i].get() + '\n')
        pfile.close()

    def LoadParams(self):
        try:
            args = self.GetParams()
            for i in range(0, len(self.input)):
                if (len(args) <= i):
                    break
                self.input[i].insert(0, args[i])
        except Exception as e:
            self.SetDefaults()

    def GetParams(self):
        params = []
        pfile = open(self.paramPath, "r")
        args = pfile.readlines()
        pfile.close()
        for arg in args:
            params.append(arg.rstrip("\n"))
        return params

    def SetDefaults(self):
        for i in range(0, len(self.input)):
            self.input[i].delete(0, "end")
            self.input[i].insert(0, self.defaults[i])


def main():
    with open(scriptPath + "\\Scripts\\flm_tools.json") as json_file:
        tools_json = json.load(json_file)

    FLM_tbx_name = []
    FLM_tbx_len = []
    FLM_tbx_desc = []
    FLM_tools = []

    for tbx in tools_json["toolbox"]:
        FLM_tbx_name.append(tbx["category"])
        FLM_tbx_len.append(len(tbx["tools"]))
        FLM_tbx_desc.append(tbx["description"])
        for tool in tbx["tools"]:
            fields = []
            types = []
            tips = []
            defaults = []
            for param in tool["parameters"]:
                fields.append(param["parameter"])
                types.append(param["type"])
                tips.append(param["description"])
                defaults.append(param["default"])

            FLM_tools.append(FLMToolDialogue(tool["name"], tool["info"], fields, types, tips, defaults,
                                             tool["scriptFile"], scriptPath + tool["paramFile"]))

    exit_code = False
    try:
        exit_code = gui.main(version, FLM_tools, 3, 2, FLM_tbx_len, FLM_tbx_name, FLM_tbx_desc)
    except Exception as e:
        flmc.log(e.message)
    if not exit_code:
        try:
            input("\n<Press any key to exit>")
        except Exception as e:
            print("")


if __name__ != '__main__':
    # If script is one of the child processes (multiprocessing) load associated scripts
    # (otherwise parallel processing is avoided)
    import Scripts.FLM_CenterLine
    import Scripts.FLM_LineFootprint
    import Scripts.FLM_Corridor
    import Scripts.FLM_CorridorFootprint
    import Scripts.FLM_ZonalThreshold
    import Scripts.FLM_ForestLineAttributes
else:
    # If script is main process, load and show GUI
    vfile = open(scriptPath + "\\Scripts\\FLM_VERSION", "r")
    args = vfile.readlines()
    vfile.close()
    version = args[0]

    flmc.newLog(version)

    print("-\nFLM  Copyright (C) 2021 Applied Geospatial Research Group")
    print("This program comes with ABSOLUTELY NO WARRANTY;\n"
          "This is free software, and you are welcome to redistribute it under certain conditions;\n"
          "See the license file distributed along with this program for details.")

    main()
