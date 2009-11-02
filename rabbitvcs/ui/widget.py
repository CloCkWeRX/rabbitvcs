#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
# 
# RabbitVCS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# RabbitVCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with RabbitVCS;  If not, see <http://www.gnu.org/licenses/>.
#

import pygtk
import gobject
import gtk

from os.path import basename

try:
    import gtkspell
    HAS_GTKSPELL = True
except ImportError:
    HAS_GTKSPELL = False

try:
    import gtksourceview
    HAS_GTKSOURCEVIEW = True
except ImportError:
    HAS_GTKSOURCEVIEW = False

import rabbitvcs.lib.helper

from rabbitvcs.lib.log import Log

log = Log("rabbitvcs.ui.widget")

TOGGLE_BUTTON = 'TOGGLE_BUTTON'
PATH_ENTRY = 'PATH_ENTRY'
SEPARATOR = u'\u2015' * 10

from pprint import pformat

def path_filter(model, iter, column, user_data):
    base_dir = user_data["base_dir"]
    path_entries = user_data["path_entries"]
    
    data = model.get_model().get_value(
                model.convert_iter_to_child_iter(iter),
                column)

    if column in path_entries:
        relpath = rabbitvcs.lib.helper.get_relative_path(base_dir, data)
        if relpath == "":
            relpath = basename(data)
        return relpath
    else:
        return data 

class Table:
    def __init__(self, treeview, coltypes, colnames, values=[], base_dir=None, path_entries=[]):
        # The list given as "path_entries" should contain the 0-indexed
        # positions of the path columns, so that the can be expressed relative
        # to "base_dir".
        
    
        self.treeview = treeview

        i = 0       
        for name in colnames:
            if name == TOGGLE_BUTTON:
                cell = gtk.CellRendererToggle()
                cell.set_property('activatable', True)
                cell.connect("toggled", self.toggled_cb, i)
                col = gtk.TreeViewColumn("", cell)
                col.set_attributes(cell, active=i)  
            else:
                cell = gtk.CellRendererText()
                cell.set_property('yalign', 0)
                col = gtk.TreeViewColumn(name, cell)
                col.set_attributes(cell, text=i)

            self.treeview.append_column(col)
            i += 1
        
        self.data = gtk.ListStore(*coltypes)
        
        # self.filter == filtered data (abs paths -> rel paths)
        # self.data == actual data
        
        # The filter is there to change the way data is displayed. The data
        # should always be accessed via self.data, NOT self.filter.
        self.filter = self.data.filter_new()
        
        user_data = {"base_dir" : base_dir,
                     "path_entries" : path_entries}
        self.filter.set_modify_func(
                        coltypes,
                        path_filter,
                        user_data)
        
        self.treeview.set_model(self.filter)
                        
        for row in values:
            self.data.append(row)
        
        self.set_resizable()

    def toggled_cb(self, cell, path, column):
        model = self.data
        model[path][column] = not model[path][column]

    def append(self, row):
        self.data.append(row)

    def remove(self, index):
        model = self.data
        del model[index]

    def remove_multiple(self, rows):
        i = 0
        for row in rows:
            rm_index = row
            if i > 0:
                rm_index -= 1
            
            self.remove(rm_index)
            i += 1     

    def get_items(self):
        return self.data

    def clear(self):
        self.data.clear()
        
    def get_row(self, index):
        model = self.data
        return model[index]
    
    def set_row(self, index, row):
        model = self.data
        model[index] = row
    
    def set_row_item(self, row, column, val):
        model = self.data
        model[row][column] = val
    
    def allow_multiple(self):
        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        
    def get_activated_rows(self, column=None):
        returner = []
        for row in self.data:
            if row[0]:
                item = row
                if column is not None:
                    item = row[column]
                
                returner.append(item)
                
        return returner
    
    def scroll_to_bottom(self):
        bottom = len(self.get_items()) - 1
        self.treeview.scroll_to_cell(bottom)

    def set_resizable(self, resizable=True):
        for col in self.treeview.get_columns():
            col.set_resizable(resizable)

    def set_column_width(self, column, width=None):
        col = self.treeview.get_column(column)
        if width is not None:
            col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            col.set_fixed_width(width)
        else:
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)

class ComboBox:
    def __init__(self, cb, items=None):
    
        self.cb = cb
    
        self.model = gtk.ListStore(str)
        if items is not None:
            for i in items:
                self.append(i)

        self.cb.set_model(self.model)

        if type(self.cb) == gtk.ComboBoxEntry:
            self.cb.set_text_column(0)
        elif type(self.cb) == gtk.ComboBox:
            cell = gtk.CellRendererText()
            self.cb.pack_start(cell, True)
            self.cb.add_attribute(cell, 'text', 0)

    def append(self, item):
        self.model.append([item])
        
    def set_active_from_value(self, value):
        index = 0
        for entry in self.model:
            if entry[0] == value:
                self.cb.set_active(index)
                return
            index += 1
    
    def get_active_text(self):
        return self.cb.get_active_text()
    
    def get_active(self):
        return self.cb.get_active()
    
    def set_active(self, index):
        self.cb.set_active(index)
    
    def set_child_text(self, text):
        self.cb.child.set_text(text)
    
    def set_sensitive(self, val):
        self.cb.set_sensitive(val)
        
class TextView:
    def __init__(self, widget=None, value=""):
        if widget is None:
            self.view = gtk.TextView()
        else:
            self.view = widget
        self.buffer = gtk.TextBuffer()
        self.view.set_buffer(self.buffer)
        self.buffer.set_text(value)
        
        if HAS_GTKSPELL:
            gtkspell.Spell(self.view)
        
    def get_text(self):
        return self.buffer.get_text(
            self.buffer.get_start_iter(), 
            self.buffer.get_end_iter()
        )
        
    def set_text(self, text):
        self.buffer.set_text(text)

class SourceView(TextView):
    def __init__(self, widget=None, value=""):
        if HAS_GTKSOURCEVIEW:
            if widget is None:
                self.view = gtksourceview.SourceView(self.buffer)
            else:
                self.view = widget
            self.buffer = gtksourceview.SourceBuffer()
            self.buffer.set_text(value)

            if HAS_GTKSPELL:
                gtkspell.Spell(self.view)

            self.view.show()
        else:
            TextView.__init__(self, widget, value)
            
class ContextMenu:
    def __init__(self, menu):
        if menu is None:
            return
        
        self.view = gtk.Menu()
        self.num_items = 0
        is_last = False
        is_first = True
        index = 0
        length = len(menu)
        for item in menu:
            is_last = (index + 1 == length)

            # If the item is a separator, don't show it if this is the first
            # or last item, or if the previous item was a separator.
            if (item["label"] == SEPARATOR and
                    (is_first or is_last or previous_label == SEPARATOR)):
                index += 1
                continue
        
            condition = item["condition"]
            if "args" in condition:
                if condition["callback"](condition["args"]) is False:
                    continue
            else:
                if condition["callback"]() is False:
                    continue
                
            menuitem = gtk.MenuItem(item["label"])
            if "signals" in item and item["signals"] is not None:
                for signal, info in item["signals"].items():
                    menuitem.connect(signal, info["callback"], info["args"])
            
            if "submenu" in item:
                submenu = ContextMenu(item["submenu"])
                menuitem.set_submenu(submenu.get_widget())
            
            self.num_items += 1
            self.view.add(menuitem)

            # The menu item above has just been added, so we can note that
            # we're no longer on the first menu item.  And we'll keep
            # track of this item so the next iteration can test if it should
            # show a separator or not
            is_first = False
            previous_label = item["label"]
            index += 1
        
    def show(self, event):        
        self.view.show_all()
        self.view.popup(None, None, None, event.button, event.time)

    def get_num_items(self):
        return self.num_items
        
    def get_widget(self):
        return self.view

class ProgressBar:
    def __init__(self, pbar):
        if pbar is None:
            self.view = gtk.ProgressBar()
        else:
            self.view = pbar
        
        self.timer = None
        
    def start_pulsate(self):
        # Set up an interval to make the progress bar pulse
        # The timeout is removed after the log action finishes
        self.timer = gobject.timeout_add(100, self.update)
    
    def stop_pulsate(self):
        if self.timer:
            gobject.source_remove(self.timer)
        self.timer = None

    def update(self, fraction=None):
        if fraction:
            if self.timer is not None:
                self.stop_pulsate()
                 
            if fraction > 1:
                fraction = 1
            self.view.set_fraction(fraction)
            return False
        else:
            self.view.pulse()
            return True

    def set_text(self, text):
        self.view.set_text(text)
