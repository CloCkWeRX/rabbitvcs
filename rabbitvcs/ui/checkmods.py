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

import thread

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.add import Add
from rabbitvcs.ui.action import VCSAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
from rabbitvcs.lib.log import Log

log = Log("rabbitvcs.ui.revert")

from rabbitvcs import gettext
_ = gettext.gettext

class CheckForModifications(InterfaceView):

    TOGGLE_ALL = True
    selected_rows = []
    selected_paths = []

    def __init__(self, paths, base_dir=None):
        InterfaceView.__init__(self, "checkmods", "CheckMods")

        self.paths = paths
        self.last_row_clicked = None
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.items = None
        self.statuses = self.vcs.STATUSES_FOR_COMMIT
        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Path"), _("Extension"), 
                _("Text Status"), _("Property Status"), _("Revision"), _("Author")],
            base_dir=base_dir,
            path_entries=[0]
        )

        self.initialize_items()

    def on_destroy(self, widget):
        self.close()
        
    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.initialize_items()

    def on_select_all_toggled(self, widget):
        self.TOGGLE_ALL = not self.TOGGLE_ALL
        for row in self.files_table.get_items():
            row[0] = self.TOGGLE_ALL

    def on_files_table_cursor_changed(self, treeview, data=None):
        self.__files_table_event(treeview, data)

    def on_files_table_button_released(self, treeview, data=None):
        self.__files_table_event(treeview, data)

    def on_files_table_key_pressed(self, treeview, data=None):
        self.update_selection(treeview)

        if gtk.gdk.keyval_name(data.keyval) == "Delete":
            self.delete_items(treeview, data)

    def on_files_table_button_pressed(self, treeview, data=None):
        # this allows us to retain multiple selections with a right-click
        if data.button == 3:
            selection = treeview.get_selection()
            (liststore, indexes) = selection.get_selected_rows()
            return (len(indexes) > 0)

    def on_files_table_row_doubleclicked(self, treeview, event, col):
        treeview.grab_focus()
        treeview.set_cursor(event[0], col, 0)
        treeview_model = treeview.get_model().get_model()
        fileinfo = treeview_model[event[0]]

        return

    def __files_table_event(self, treeview, data=None):
        self.update_selection(treeview)
            
        if data is not None and data.button == 3:
            self.show_files_table_popup_menu(treeview, data)

    #
    # Helper methods
    #

    def initialize_items(self):
        """
        Initializes the file items in a new thread
        """
        
        try:
            thread.start_new_thread(self.load, ())
        except Exception, e:
            log.exception(e)

    def load(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))
        self.items = self.vcs.get_remote_updates(self.paths)
        self.populate_files_table()
        self.get_widget("status").set_text(_("Found %d item(s)") % len(self.items))
        gtk.gdk.threads_leave()

    def populate_files_table(self):
        self.files_table.clear()
        for item in self.items:
            self.files_table.append([
                item.path, 
                rabbitvcs.lib.helper.get_file_extension(item.path),
                item.repos_text_status,
                item.repos_prop_status,
                str(item.entry.revision.number),
                item.entry.commit_author
            ])

    def update_selection(self, treeview):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        self.selected_paths = []
        for tup in indexes:
            self.selected_rows.append(tup[0])
            self.selected_paths.append(self.files_table.get_row(tup[0])[0])

    def show_files_table_popup_menu(self, treeview, data):
        # Generate the full context menu
        context_menu = rabbitvcs.ui.widget.ContextMenu([
            {
                "label": _("Update"),
                "signals": {
                    "activate": {
                        "callback": self.on_context_update_activated, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.condition_update
                }
            }
        ])
        context_menu.show(data)

    #
    # Context menu callbacks
    #
    
    def on_context_update_activated(self, widget, data=None):
        rabbitvcs.lib.helper.launch_ui_window("update", self.selected_paths)
    
    #
    # Context menu conditions
    #

    def condition_update(self, data=None):
        return True

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main()

    window = CheckForModifications(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
