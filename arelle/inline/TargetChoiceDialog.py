"""
See COPYRIGHT.md for copyright information.
"""
import regex as re


class TargetChoiceDialog:
    def __init__(self,parent, choices):
        from tkinter import Toplevel, Label, Listbox, StringVar
        parentGeometry = re.match(r"(\d+)x(\d+)[+]?([-]?\d+)[+]?([-]?\d+)", parent.geometry())
        dialogX = int(parentGeometry.group(3))
        dialogY = int(parentGeometry.group(4))
        self.parent = parent
        self.t = Toplevel()
        self.t.transient(self.parent)
        self.t.geometry("+{0}+{1}".format(dialogX+200,dialogY+200))
        self.t.title(_("Select Target"))
        self.selection = choices[0] # default choice in case dialog is closed without selecting an entry
        self.lb = Listbox(self.t, height=10, width=30, listvariable=StringVar(value=choices))
        self.lb.grid(row=0, column=0)
        self.lb.focus_set()
        self.lb.bind("<<ListboxSelect>>", self.select)
        self.t.grab_set()
        self.t.wait_window(self.t)

    def select(self,event):
        self.parent.focus_set()
        self.selection = self.lb.selection_get()
        self.t.destroy()
