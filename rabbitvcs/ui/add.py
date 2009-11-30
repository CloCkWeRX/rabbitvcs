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

import os
import thread
from time import sleep

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.lib.contextmenu import GtkFilesContextMenu, GtkContextMenuCaller
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
import rabbitvcs.lib.vcs
from rabbitvcs.lib.log import Log

log = Log("rabbitvcs.ui.add")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class Add(InterfaceView, GtkContextMenuCaller):
    """
    Provides an interface for the user to add unversioned files to a
    repository.  Also, provides a context menu with some extra functionality.
    
    Send a list of paths to be added
    
    """

    TOGGLE_ALL = True

    def __init__(self, paths, base_dir=None):
        InterfaceView.__init__(self, "add", "Add")
        
        self.paths = paths
        self.base_dir = base_dir
        self.last_row_clicked = None
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.items = []
        self.statuses = [self.vcs.STATUS["unversioned"], self.vcs.STATUS["obstructed"]]
        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_BOOLEAN, rabbitvcs.ui.widget.TYPE_PATH, 
                gobject.TYPE_STRING],
            [rabbitvcs.ui.widget.TOGGLE_BUTTON, _("Path"), _("Extension")],
            filters=[{
                "callback": rabbitvcs.ui.widget.path_filter,
                "user_data": {
                    "base_dir": base_dir,
                    "column": 1
                }
            }],
            callbacks={
                "row-activated":  self.on_files_table_row_activated,
                "mouse-event":   self.on_files_table_mouse_event,
                "key-event":     self.on_files_table_key_event
            }
        )

        self.initialize_items()

    #
    # Helpers
    #

    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_items(self.paths, self.statuses)
        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))
        gtk.gdk.threads_leave()

    def populate_files_table(self):
        self.files_table.clear()
        for item in self.items:
            self.files_table.append([
                True, 
                item.path, 
                rabbitvcs.lib.helper.get_file_extension(item.path)
            ])

    def reload_treeview(self):
        self.initialize_items()

    def reload_treeview_threaded(self):
        self.load()

    def initialize_items(self):
        """
        Initializes the activated cache and loads the file items in a new thread
        """
        
        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception(e)

    def delete_items(self, widget, data=None):
        paths = self.files_table.get_selected_row_items(1)
        if len(paths) > 0:
            from rabbitvcs.ui.delete import Delete
            Delete(paths).start()
            sleep(1) # sleep so the items can be fully deleted before init
            self.initialize_items()
    
    #
    # UI Signal Callbacks
    #
    
    def on_destroy(self, widget):
        self.close()
        
    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        items = self.files_table.get_activated_rows(1)
        if not items:
            self.close()
            return

        self.hide()

        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Add"))
        self.action.append(self.action.set_status, _("Running Add Command..."))
        self.action.append(self.vcs.add, items)
        self.action.append(self.action.set_status, _("Completed Add"))
        self.action.append(self.action.finish)
        self.action.start()

    def on_select_all_toggled(self, widget):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(1)
        rabbitvcs.lib.helper.launch_diff_tool(*paths)

    def on_files_table_key_event(self, treeview, data=None):
        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            self.delete_items(treeview, data)

    def on_files_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_files_table_popup_menu(treeview, data)

    def show_files_table_popup_menu(self, treeview, data):
        paths = self.files_table.get_selected_row_items(1)
        GtkFilesContextMenu(self, data, self.base_dir, paths).show()

class AddQuiet:
    def __init__(self, paths):
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            run_in_thread=False
        )
        
        self.action.append(self.vcs.add, paths)
        self.action.run()

if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT, QUIET_OPT
    (options, paths) = main(
        [BASEDIR_OPT, QUIET_OPT],
        usage="Usage: rabbitvcs add [path1] [path2] ..."
    )

    if options.quiet:
        AddQuiet(paths)
    else:
        window = Add(paths, options.base_dir)
        window.register_gtk_quit()
        gtk.main()
