# ---------------------------------------------------------------------------
#
# Tooltip.py
# Script Author: SquareRoot17, retrieved at 01/01/2020 from https://stackoverflow.com/questions/20399243/display-message-when-hovering-over-something-with-mouse-cursor-in-python
# Modified by Gustavo Lopes Queiroz
# Date: 2020-Jan-22
#
# Purpose: Allows for GUI tooltips when user hovers the cursor over elements
#
# ---------------------------------------------------------------------------
try:
    from tkinter import *
except ImportError:
    from Tkinter import *
    
class ToolTip(object):

    def __init__(self, widget, wraplength = 0):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.wraplength = wraplength

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1, wraplength = self.wraplength,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def CreateToolTip(widget, text, wraplength = 0):
    toolTip = ToolTip(widget, wraplength)
    def enter(event):
        toolTip.showtip(text)
    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)