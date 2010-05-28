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
from rabbitvcs.util.contextmenu import GtkContextMenu, \
    GtkContextMenuCaller, GtkFilesContextMenuConditions
from rabbitvcs.util.contextmenuitems import MenuItem, MenuUpdate, MenuSeparator
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.util.helper
from rabbitvcs.util.log import Log
from rabbitvcs.util.decorators import gtk_unsafe

log = Log("rabbitvcs.ui.checkmods")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class SVNCheckForModifications(InterfaceView, GtkContextMenuCaller):
    """
    Provides a way for the user to see what files have been changed on the 
    repository.
    
    """
    
    def __init__(self, paths, base_dir=None):
        InterfaceView.__init__(self, "checkmods", "CheckMods")

        self.paths = paths
        self.base_dir = base_dir
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()
        self.items = None
        self.files_table = rabbitvcs.ui.widget.Table(
            self.get_widget("files_table"), 
            [gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Path"), _("Extension"), 
                _("Text Status"), _("Property Status"), 
                _("Revision"), _("Author")],
            filters=[{
                "callback": rabbitvcs.ui.widget.path_filter,
                "user_data": {
                    "base_dir": base_dir,
                    "column": 0
                }
            }],
            callbacks={
                "row-activated":  self.on_files_table_row_activated,
                "mouse-event":   self.on_files_table_mouse_event
            }
        )

        self.load()

    def on_destroy(self, widget):
        self.destroy()
        
    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.load()

    def on_files_table_row_activated(self, treeview, event, col):
        paths = self.files_table.get_selected_row_items(0)
        self.diff_remote(paths[0])

    def on_files_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_files_table_popup_menu(treeview, data)

    #
    # Helper methods
    #
    
    def load(self):
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(self.svn.get_remote_updates, self.paths)
        self.action.append(self.populate_files_table)
        self.action.start()

    @gtk_unsafe
    def populate_files_table(self):
        self.files_table.clear()
        self.items = self.action.get_result(0)
        for item in self.items:
            revision_number = -1
            author = ""
            if item.entry is not None:
                revision_number = item.entry.revision.number
                author = item.entry.commit_author

            self.files_table.append([
                item.path, 
                rabbitvcs.util.helper.get_file_extension(item.path),
                item.repos_text_status,
                item.repos_prop_status,
                str(revision_number),
                author
            ])

    def show_files_table_popup_menu(self, treeview, data):
        paths = self.files_table.get_selected_row_items(0)
        CheckModsContextMenu(self, data, self.base_dir, self.vcs, paths).show()
     
    def diff_remote(self, path):
        from rabbitvcs.ui.diff import SVNDiff
        
        path_local = path
        path_remote = self.svn.get_repo_url(path_local)
        
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(
            SVNDiff,
            path_local, 
            None, 
            path_remote,
            "HEAD"
        )
        self.action.start()

class MenuViewDiff(MenuItem):
    identifier = "RabbitVCS::View_Diff"
    label = _("View unified diff")
    icon = "rabbitvcs-diff"

class MenuCompare(MenuItem):
    identifier = "RabbitVCS::Compare"
    label = _("Compare side by side")
    icon = "rabbitvcs-compare"

class CheckModsContextMenuConditions(GtkFilesContextMenuConditions):
    def __init__(self, vcs, paths=[]):
        GtkFilesContextMenuConditions.__init__(self, vcs, paths)

    def update(self, data=None):
        return True

    def view_diff(self, data=None):
        return (self.path_dict["exists"]
            and self.path_dict["length"] == 1)

    def compare(self, data=None):
        return (self.path_dict["exists"]
            and self.path_dict["length"] == 1)

class CheckModsContextMenuCallbacks:
    def __init__(self, caller, base_dir, vcs, paths=[]):
        self.caller = caller
        self.base_dir = base_dir
        self.vcs = vcs
        self.svn = self.vcs.svn()
        self.paths = paths

    def update(self, data1=None, data2=None):
        rabbitvcs.util.helper.launch_ui_window(
            "update", 
            self.paths
        )

    def view_diff(self, data1=None, data2=None):
        self.caller.diff_remote(self.paths[0])

    def compare(self, data1=None, data2=None):
        from rabbitvcs.ui.diff import SVNDiff
        
        path_local = self.paths[0]
        path_remote = self.svn.get_repo_url(path_local)
        
        self.action = rabbitvcs.ui.action.SVNAction(
            self.svn,
            notification=False
        )
        self.action.append(
            SVNDiff,
            path_local, 
            None, 
            path_remote,
            "HEAD",
            sidebyside=True
        )
        self.action.start()

class CheckModsContextMenu:
    def __init__(self, caller, event, base_dir, vcs, paths=[]):
        
        self.caller = caller
        self.event = event
        self.paths = paths
        self.base_dir = base_dir
        self.vcs = vcs
        
        self.conditions = CheckModsContextMenuConditions(self.vcs, paths)
        self.callbacks = CheckModsContextMenuCallbacks(
            self.caller, 
            self.base_dir,
            self.vcs, 
            paths
        )
        
        self.structure = [
            (MenuViewDiff, None),
            (MenuCompare, None),
            (MenuSeparator, None),
            (MenuUpdate, None)
        ]

    def show(self):
        if len(self.paths) == 0:
            return

        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNCheckForModifications
}

def checkmods_factory(paths, base_dir):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths, base_dir)

if __name__ == "__main__":
    from rabbitvcs.ui import main, BASEDIR_OPT
    (options, paths) = main(
        [BASEDIR_OPT],
        usage="Usage: rabbitvcs checkmods [url_or_path]"
    )

    window = checkmods_factory(paths, options.base_dir)
    window.register_gtk_quit()
    gtk.main()
