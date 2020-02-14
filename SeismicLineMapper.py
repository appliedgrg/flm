# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Seismic line Mapper
# Date: 2020-Jan-22
#
# Development history:
#   Worflow overhaul by Gustavo Lopes Queiroz, November, 2019
#   First version in Arcpy by Silvia Losada, November 2018
#   Initial concept by Sarah Cole and Jerome Cranston, May 2018
#   
# Citation: Applied Geospatial Research Group, 2020. Seismic Line Mapper: 
# A tool for enhanced delineation and attribution of linear disturbances in 
# forests.
#
# SLM is a series of script tools for facilitating the high-resolution mapping 
# and studying of seismic lines (petroleum exploration corridors in forested 
# areas) via processing canopy height models (LiDAR or photogrammetry derived 
# raster images where pixel-values represent the ground-height of vegetation).
#
# Usage: Follow the instructions available in the SLM webpage.
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# ---------------------------------------------------------------------------
#
#    Copyright (C) 2020  Applied Geospatial Research Group
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
# SeismicLineMapper.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Seismic Line Mapper (SLM) toolset
# Webpage: https://github.com/appliedgrg/seismic-line-mapper
#
# Purpose: This script contains the tool names, parameters and decriptions.
# GUI is constructed based on calls contained within this script. 
#
# ---------------------------------------------------------------------------
	
version = ""

class SLM_Tool_GUI:
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
		entries = gui.ToolSetup( toolScreen, self.title, self.description, self.fields, self.types, self.tips, self.scriptFile, self.paramPath )
		self.input = entries
		self.LoadParams()
	def OpenTool(self):
		gui.OpenScreen( self, self.toolScreen )
	def SaveParams(self):
		pfile = open(self.paramPath,"w")
		for i in range (0,len(self.input) ):
			pfile.write(self.input[i].get()+'\n')
		pfile.close()
	def LoadParams(self):
		try:
			args = self.GetParams()
			for i in range (0,len(self.input) ):
				if(len(args)<=i):
					break
				self.input[i].insert(0, args[i])
		except:
			self.SetDefaults()
	def GetParams(self):
		params = []
		pfile = open(self.paramPath,"r")
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

	with open(scriptPath+"\\Scripts\\slm_tools.json") as json_file:
		tools_json = json.load(json_file)
		
	SLM_tbx_name = []
	SLM_tbx_len = []
	SLM_tbx_desc = []
	SLM_tools = []
	
	for tbx in tools_json["toolbox"]:
		SLM_tbx_name.append(tbx["category"])
		SLM_tbx_len.append(len(tbx["tools"]))
		SLM_tbx_desc.append(tbx["description"])
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
			SLM_tools.append(SLM_Tool_GUI(tool["name"], tool["info"], fields, types, tips, defaults, tool["scriptFile"], scriptPath+tool["paramFile"]))
	
	exit = False
	try:
		exit = gui.main(version,SLM_tools,2,2,SLM_tbx_len,SLM_tbx_name,SLM_tbx_desc)
	except Exception as e: 
		slmc.log(e.message)
	if(exit == False):
		try:
			input("\n<Press any key to exit>")
		except:
			print("")
		
if __name__ != '__main__':
	#If script is one of the child processes (multiprocessing) load associated scripts (otherwise parallel processing is avoided)
	import Scripts.SLM_CenterLine
	import Scripts.SLM_LineFootprint
	import Scripts.SLM_Corridor
	import Scripts.SLM_CorridorFootprint
	import Scripts.SLM_ZonalThreshold
	import Scripts.SLM_SeismicLineAttributes
else:
	#If script is main process, load and show GUI
	import os
	scriptPath = os.path.dirname(os.path.realpath(__file__))
	
	vfile = open(scriptPath+"\\Scripts\\SLM_VERSION","r")
	args = vfile.readlines()
	vfile.close()
	version = args[0]

	import json
	import Scripts.SLM_Common as slmc
	import Scripts.SLM_GUI_Tools as gui
	
	slmc.newLog(version)
		
	print("-\nSLM  Copyright (C) 2020  Applied Geospatial Research Group")
	print("This program comes with ABSOLUTELY NO WARRANTY;\nThis is free software, and you are welcome to redistribute it under certain conditions;\nSee the license file distributed along with this program for details.")
		
	main()
		