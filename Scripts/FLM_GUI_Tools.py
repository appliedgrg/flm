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
# FLM_GUI_Tools.py
# Script Author: Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# This script is part of the Forest Line Mapper (FLM) toolset
# Webpage: https://github.com/appliedgrg/flm
#
# Purpose: Handles the GUI construction and interaction for FLM tools.
#
# ---------------------------------------------------------------------------

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    import Tkinter as tk
    import ttk
try:
    import tkFileDialog
except ImportError:
    import tkinter.filedialog as tkFileDialog
import os
import importlib
import webbrowser
import multiprocessing
import Tooltip as ttp
import FLM_Common as flmc

# Initialize GUI
scriptPath = os.path.dirname(os.path.realpath(__file__))
master = tk.Tk()
master.title("Forest Line Mapper")
minWidth = 420
master.minsize(minWidth, 320)
help_url = "http://flm.beraproject.org/"
fontHeader = 'Helvetica 12 bold'
fontText = 'Helvetica 10'
fontBold = 'Helvetica 10 bold'


def RunTool():
    currentTool.SaveParams()
    master.destroy()
    print("Initializing arcpy and other script dependencies...")
    scriptTool = importlib.import_module(currentTool.scriptFile)
    flmc.logStart(currentTool)
    try:
        r = scriptTool.main()
        if (r != False):
            flmc.logEnd(currentTool)
    except Exception as e:
        flmc.log("\n".join(e.args))


def ToolDefaults():
    currentTool.SetDefaults()


def AddSpace(frame):
    rowSpace = tk.Frame(frame)
    rowSpace.pack(side=tk.TOP, fill=tk.X, pady=5)


def ExitAndSave():
    currentTool.SaveParams()
    global userExit
    userExit = True
    master.destroy()


def Exit():
    global userExit
    userExit = True
    master.destroy()


def SelectFile(entryField, type, name):
    FILEOPENOPTIONS = dict(defaultextension=type, title=name, initialdir=os.path.dirname(entryField.get()),
                           filetypes=[(type, "*" + type), ('All files', '*.*')])
    if name.lower().count("output") == 0:
        file_path = tkFileDialog.askopenfilename(**FILEOPENOPTIONS)
    else:
        file_path = tkFileDialog.asksaveasfilename(**FILEOPENOPTIONS)
    if file_path == "":
        return False
    entryField.delete(0, "end")
    entryField.insert(0, file_path)


def makeform(root, fields, types, tips, toolScript, paramFile):
    entries = []
    toolBox = tk.Frame(root, highlightbackground="gray60", highlightthickness=1)
    for i in range(0, len(fields)):
        rowLab = tk.Frame(toolBox)
        lab = tk.Label(rowLab, text=fields[i], anchor='w')
        lab.pack(side=tk.LEFT)
        ttp.CreateToolTip(lab, tips[i], wraplength=minWidth)
        rowLab.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)

        isList = (types[i][:5] == 'list:')
        rowEnt = tk.Frame(toolBox)
        if isList == True:
            ent = ttk.Combobox(rowEnt, values=types[i][5:].split(","))
        elif (types[i] != "bool"):
            ent = tk.Entry(rowEnt)
        else:
            ent = ttk.Combobox(rowEnt, values=["False", "True"])

        rowEnt.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0, anchor=tk.N)
        if isList == False and types[i] != "number" and types[i] != "string" and types[i] != "bool":
            but = tk.Button(rowEnt, text='...', command=lambda i=i, ent=ent: SelectFile(ent, types[i], fields[i]))
            but.pack(side=tk.RIGHT)
        ent.pack(side=tk.LEFT, expand=tk.YES, fill=tk.X, padx=5)
        entries.append(ent)
        AddSpace(toolBox)
    toolBox.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=5, pady=0)

    # Buttons
    row = tk.Frame(root)
    but = tk.Button(row, text='BACK', command=lambda: BackToSelection())
    but.pack(side=tk.RIGHT, padx=5)
    but = tk.Button(row, text='HELP', command=lambda: webbrowser.open(help_url))
    but.pack(side=tk.RIGHT, padx=5)
    but = tk.Button(row, text='DEFAULTS', command=lambda: ToolDefaults())
    but.pack(side=tk.RIGHT, padx=5)
    but = tk.Button(row, text='RUN TOOL', command=lambda: RunTool())
    but.pack(side=tk.RIGHT, padx=5)
    row.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=10)

    return entries


def ToolSetup(toolScreen, title, description, fields, types, tips, toolScript, paramFile):
    lab = tk.Label(toolScreen, text=title, font=fontHeader)
    lab.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)
    lab = tk.Label(toolScreen, text=description.replace("\n", " "), font=fontText, wraplength=minWidth, justify=tk.LEFT)
    lab.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)
    AddSpace(toolScreen)
    entries = makeform(toolScreen, fields, types, tips, toolScript, paramFile)
    return entries


def OpenScreen(toolObj, screen):
    # Save cores
    flmc.SetCores(mpc.get())
    # Close tool selection screen
    toolSelection.pack_forget()
    # Close other tool screens
    for toolScreen in toolScreens:
        toolScreen.pack_forget()
    # Open current tool screen
    screen.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=5, pady=0)
    # Set current tool obj for referencing inputs
    global currentTool
    currentTool = toolObj


def BackToSelection():
    global currentTool
    currentTool.SaveParams()
    currentTool = None
    # Close tool screens
    for toolScreen in toolScreens:
        toolScreen.pack_forget()
    # Open tool selection screen
    toolSelection.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=5, pady=0)


# GLOBAL VARS
# Header image 
rowHead = tk.Frame(master)
photo = tk.PhotoImage(file=scriptPath + "//..//Images//FLM_banner.gif")
header = tk.Label(rowHead, image=photo)
header.image = photo  # keep a reference!
header.pack(side=tk.TOP)
rowHead.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)
mpc = None
# Space between header and body
AddSpace(master)
# Body
toolSelection = tk.Frame(master)
toolScreens = []
# Current tool
currentTool = None
# Flag if user wants to exit
userExit = False


def main(version, tools, cols, rows, binSizes, binNames, binTips):
    """Creates tool selection screen and handles GUI loop"""

    master.title("Forest Line Mapper v." + str(version))
    # FLM Header
    lab = tk.Label(toolSelection, text="Forest Line Mapper", font=fontHeader)
    lab.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)
    lab = tk.Label(toolSelection, text="A toolset for enhanced delineation and attribution of linear disturbances "
                                       "in forests. Copyright (C) 2019 Applied Geospatial Research Group.",
                   font=fontText, wraplength=minWidth, justify=tk.LEFT)
    lab.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)
    AddSpace(toolSelection)

    # Create tool bins inside toolbox
    toolBox = tk.Frame(toolSelection, highlightbackground="gray60", highlightthickness=1)
    bins = []
    for i in range(0, cols):
        binCol = tk.Frame(toolBox)
        binCol.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES, padx=0, pady=0)
        c = []
        for j in range(0, rows):
            bin = tk.Frame(binCol)
            bin.pack(side=tk.TOP, fill=tk.X, padx=0, pady=8)
            binId = i * rows + j
            binName = tk.Label(bin, text=binNames[binId], font=fontBold)
            binName.pack(side=tk.TOP, pady=0)
            ttp.CreateToolTip(binName, binTips[binId], wraplength=minWidth)
            c.append(bin)
        bins.append(c)

    binId = 0
    binLen = 0

    for tool in tools:
        # Figue out the bin where to place the tool
        if binLen >= binSizes[binId]:
            binId += 1
            binLen = 0
        col = int(binId / rows)
        row = binId % rows
        currentBin = bins[col][row]
        binLen += 1

        # Tool object
        currentTool = tool

        # Tool selection button
        row = tk.Frame(currentBin)
        but = tk.Button(row, text=tool.title, command=lambda tool=tool: tool.OpenTool())
        ttp.CreateToolTip(but, tool.description, wraplength=minWidth)
        but.pack(padx=5)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Tool screen and inputs
        toolScreen = tk.Frame(master)
        toolScreens.append(toolScreen)
        tool.SetupTool(toolScreen)

    currentTool = None
    toolBox.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=5, pady=0)

    # Multiprocessing cores
    row = tk.Frame(toolSelection)
    lab = tk.Label(row, text="Multiprocessing Cores")
    ttp.CreateToolTip(lab,
                      "The number of CPU cores to be used in parallel processes. Not all FLM tools use "
                      "multiprocessing.\nFor the most part a larger number of cores will decrease processing time. "
                      "Small application \nareas (<100 hectares) may work best with a smaller number of cores.")
    lab.pack(side=tk.LEFT, padx=5, pady=0)
    global mpc
    maxCores = multiprocessing.cpu_count()
    mpc = tk.Scale(row, from_=1, to=maxCores, orient="horizontal")
    mpc.set(flmc.GetCores())
    mpc.pack(side=tk.TOP, fill=tk.X, padx=5, pady=0)
    row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=10)

    # Footer Buttons
    row = tk.Frame(toolSelection)
    but = tk.Button(row, text='EXIT', command=lambda: Exit())
    but.pack(side=tk.RIGHT, padx=5)
    but = tk.Button(row, text='HELP', command=lambda: webbrowser.open(help_url))
    but.pack(side=tk.RIGHT, padx=5)
    row.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=10)
    toolSelection.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=5, pady=0)

    master.protocol("WM_DELETE_WINDOW", Exit)
    tk.mainloop()
    return userExit
