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

import os.path
import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.util.helper
from rabbitvcs.util.contextmenu import GtkContextMenu
from rabbitvcs.util.contextmenuitems import *
from rabbitvcs.ui.log import LogDialog
from rabbitvcs.ui.action import VCSAction
from rabbitvcs.ui.dialog import MessageBox
from rabbitvcs import gettext
_ = gettext.gettext

class Changes(InterfaceView):
    """
    Show how files and folders are different between revisions.
    
        TODO:
            - Deal with the revision arguments in a smarter way so we can pass
                in revisions like HEAD.  Currently, if a revision is passed it
                assumes it is a number
    """
    selected_rows = []
    MORE_ACTIONS_ITEMS = [
        _("More Actions..."),
        _("View unified diff")
    ]

    def __init__(self, path1=None, revision1=None, path2=None, revision2=None):
        InterfaceView.__init__(self, "changes", "Changes")
        
        self.vcs = rabbitvcs.vcs.create_vcs_instance()

        self.MORE_ACTIONS_CALLBACKS = [
            None,
            self.on_more_actions_view_unified_diff
        ]

        self.more_actions = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("more_actions"),
            self.MORE_ACTIONS_ITEMS
        )
        self.more_actions.set_active(0)

        repo_paths = rabbitvcs.util.helper.get_repository_paths()
        self.first_urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("first_urls"), 
            repo_paths
        )
        self.first_urls_browse = self.get_widget("first_urls_browse")

        self.second_urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("second_urls"), 
            repo_paths
        )
        self.second_urls_browse = self.get_widget("second_urls_browse")

        self.first_revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("first_revision_container"),
            self.vcs,
            revision=revision1,
            url_combobox=self.first_urls
        )

        self.second_revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("second_revision_container"),
            self.vcs,
            revision=revision2,
            url_combobox=self.second_urls
        )

        if path1 is not None:
            self.first_urls.set_child_text(self.vcs.get_repo_url(path1))
            
        if path2 is not None:
            self.second_urls.set_child_text(self.vcs.get_repo_url(path2))
        elif path1 is not None:
            self.second_urls.set_child_text(self.vcs.get_repo_url(path1))

        self.changes_table = rabbitvcs.ui.widget.Table(
            self.get_widget("changes_table"),
            [rabbitvcs.ui.widget.TYPE_PATH, gobject.TYPE_STRING, 
                gobject.TYPE_STRING], 
            [_("Path"), _("Change"), _("Property Change")]
        )
        
        self.check_ui()
        
        if path1 and revision1 and path2 and revision2:
            self.load()

    #
    # UI Signal Callback Methods
    #

    def on_destroy(self, widget):
        self.close()

    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.load()
    
    def on_first_urls_changed(self, widget, data=None):
        self.check_first_urls()
        self.first_revision_selector.determine_widget_sensitivity()
        self.check_refresh_button()

    def on_second_urls_changed(self, widget, data=None):
        self.check_second_urls()
        self.second_revision_selector.determine_widget_sensitivity()
        self.check_refresh_button()

    def on_first_urls_browse_clicked(self, widget, data=None):
        from rabbitvcs.ui.browser import BrowserDialog
        BrowserDialog(self.first_urls.get_active_text(), 
            callback=self.on_first_repo_chooser_closed)

    def on_first_repo_chooser_closed(self, new_url):
        self.first_urls.set_child_text(new_url)
        self.check_first_urls()
        self.first_revision_selector.determine_widget_sensitivity()
        self.check_refresh_button()

    def on_second_urls_browse_clicked(self, widget, data=None):
        from rabbitvcs.ui.browser import BrowserDialog
        BrowserDialog(self.second_urls.get_active_text(), 
            callback=self.on_second_repo_chooser_closed)

    def on_second_repo_chooser_closed(self, new_url):
        self.second_urls.set_child_text(new_url)
        self.check_second_urls()
        self.second_revision_selector.determine_widget_sensitivity()
        self.check_refresh_button()

    def on_changes_table_cursor_changed(self, treeview, data=None):
        self.on_changes_table_event(treeview, data)

    def on_changes_table_button_released(self, treeview, data=None):
        self.on_changes_table_event(treeview, data)

    def on_changes_table_event(self, treeview, data=None):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

        if data is not None and data.button == 3:
            self.show_changes_table_popup_menu(treeview, data)

    def on_more_actions_changed(self, widget, data=None):
        index = self.more_actions.get_active()
        if index < 0:
            return
            
        callback = self.MORE_ACTIONS_CALLBACKS[index]
        
        if callback is not None:
            callback()

    def on_changes_table_row_doubleclicked(self, treeview, data=None, col=None):
        selection = treeview.get_selection()
        (liststore, indexes) = selection.get_selected_rows()

        self.selected_rows = []
        for tup in indexes:
            self.selected_rows.append(tup[0])

        self.view_selected_diff(sidebyside=True)

    #
    # Helper methods
    #
    
    def get_first_revision(self):
        return self.first_revision_selector.get_revision_object()
    
    def get_second_revision(self):
        return self.second_revision_selector.get_revision_object()

    def show_changes_table_popup_menu(self, treeview, data):
        ChangesContextMenu(self, data).show()
    
    def check_ui(self):
        self.check_first_urls()
        self.check_second_urls()
        self.first_revision_selector.determine_widget_sensitivity()
        self.second_revision_selector.determine_widget_sensitivity()
        self.check_refresh_button()
    
    def can_first_browse_urls(self):
        return (self.first_urls.get_active_text() != "")
    
    def can_second_browse_urls(self):
        return (self.second_urls.get_active_text() != "")
    
    def check_refresh_button(self):
        can_click_refresh = (
            self.can_first_browse_urls()
            and self.can_second_browse_urls()
        )
        
        self.get_widget("refresh").set_sensitive(can_click_refresh)
    
    def check_first_urls(self):
        can_browse_urls = self.can_first_browse_urls()
        self.first_urls_browse.set_sensitive(can_browse_urls)
        
    def check_second_urls(self):
        can_browse_urls = self.can_second_browse_urls()
        self.second_urls_browse.set_sensitive(can_browse_urls)

    def load(self):
        first_url = self.first_urls.get_active_text()
        first_rev = self.get_first_revision()
        second_rev = self.get_second_revision()        
        second_url = self.second_urls.get_active_text()

        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(self.disable_more_actions)
        self.action.append(
            self.vcs.diff_summarize,
            first_url,
            first_rev,
            second_url,
            second_rev
        )
        self.action.append(rabbitvcs.util.helper.save_repository_path, first_url)
        self.action.append(rabbitvcs.util.helper.save_repository_path, second_url)
        self.action.append(self.populate_table)
        self.action.append(self.enable_more_actions)
        self.action.start()

    def populate_table(self):
        # returns a list of dicts(path, summarize_kind, node_kind, prop_changed)
        summary = self.action.get_result(1)

        self.changes_table.clear()
        for item in summary:
            prop_changed = (item["prop_changed"] == 1 and _("Yes") or _("No"))
            
            path = item["path"]
            if path == "":
                path = "."
                
            self.changes_table.append([
                path,
                item["summarize_kind"],
                prop_changed
            ])

    def enable_more_actions(self):
        self.more_actions.set_sensitive(True)

    def disable_more_actions(self):
        self.more_actions.set_sensitive(False)

    def open_item_from_revision(self, url, revision, dest):
        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            self.vcs.export,
            url,
            dest,
            revision=revision
        )
        self.action.append(rabbitvcs.util.helper.open_item, dest)
        self.action.start()
    
    def view_selected_diff(self, sidebyside=False):
        from rabbitvcs.ui.diff import SVNDiff
        url1 = self.changes_table.get_row(self.selected_rows[0])[0]
        url2 = url1
        if url1 == ".":
            url1 = ""
            url2 = ""

        url1 = rabbitvcs.util.helper.url_join(self.first_urls.get_active_text(), url1)
        url2 = rabbitvcs.util.helper.url_join(self.second_urls.get_active_text(), url2)
        rev1 = self.get_first_revision()
        rev2 = self.get_second_revision()

        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            SVNDiff,
            url1, 
            (rev1.value and rev1.value or "HEAD"), 
            url2, 
            (rev2.value and rev2.value or "HEAD"),
            sidebyside=sidebyside
        )
        self.action.start()
        
    #
    # More Actions callbacks
    #

    def on_more_actions_view_unified_diff(self):
        from rabbitvcs.ui.diff import SVNDiff
        
        first_url = self.first_urls.get_active_text()
        first_rev = self.get_first_revision()
        second_rev = self.get_second_revision()        
        second_url = self.second_urls.get_active_text()

        self.action = VCSAction(
            self.vcs,
            notification=False
        )
        self.action.append(
            SVNDiff,
            first_url, 
            (first_rev.value and first_rev.value or "HEAD"), 
            second_url, 
            (second_rev.value and second_rev.value or "HEAD")
        )
        self.action.start()



class MenuOpenFirst(MenuItem):
    identifier = "RabbitVCS::Open_First"
    label = _("Open from first revision")
    icon = gtk.STOCK_OPEN

class MenuOpenSecond(MenuItem):
    identifier = "RabbitVCS::Open_Second"
    label = _("Open from second revision") 
    icon = gtk.STOCK_OPEN
    
class MenuViewDiff(MenuItem):
    identifier = "RabbitVCS::View_Diff"
    label = _("View unified diff")   
    icon = "rabbitvcs-diff"

class MenuCompare(MenuItem):
    identifier = "RabbitVCS::Compare"
    label = _("Compare side by side")
    icon = "rabbitvcs-compare"

class ChangesContextMenuConditions:
    def __init__(self, caller, vcs_client):
        self.caller = caller
        self.vcs_client = vcs_client

    def open_first(self):
        return (
            len(self.caller.selected_rows) == 1
        )
    
    def open_second(self):
        return (
            len(self.caller.selected_rows) == 1 
            and (
                str(self.caller.get_first_revision()) != str(self.caller.get_second_revision())
                or self.caller.first_urls.get_active_text() != self.caller.second_urls.get_active_text()
            )
        )

    def view_diff(self):
        return (
            len(self.caller.selected_rows) == 1
        )

    def compare(self):
        return (
            len(self.caller.selected_rows) == 1
        )

class ChangesContextMenuCallbacks:
    def __init__(self, caller, vcs_client):
        self.caller = caller
        self.vcs_client = vcs_client

    def open_first(self, widget, data=None):
        path = self.caller.changes_table.get_row(self.caller.selected_rows[0])[0]
        if path == ".":
            path = ""

        url = rabbitvcs.util.helper.url_join(self.caller.first_urls.get_active_text(), path)
        rev = self.caller.get_first_revision()
        dest = "/tmp/rabbitvcs-" + str(rev) + "-" + os.path.basename(url)
        self.caller.open_item_from_revision(url, rev, dest)

    def open_second(self, widget, data=None):
        path = self.caller.changes_table.get_row(self.caller.selected_rows[0])[0]
        if path == ".":
            path = ""
        
        url = rabbitvcs.util.helper.url_join(self.caller.second_urls.get_active_text(), path)
        rev = self.caller.get_second_revision()
        dest = "/tmp/rabbitvcs-" + str(rev) + "-" + os.path.basename(url)
        self.caller.open_item_from_revision(url, rev, dest)

    def view_diff(self, widget, data=None):
        self.caller.view_selected_diff()

    def compare(self, widget, data=None):
        url1 = self.caller.changes_table.get_row(self.caller.selected_rows[0])[0]
        url2 = url1
        if url1 == ".":
            url1 = ""
            url2 = ""

        url1 = rabbitvcs.util.helper.url_join(self.caller.first_urls.get_active_text(), url1)
        url2 = rabbitvcs.util.helper.url_join(self.caller.second_urls.get_active_text(), url2)
        rev1 = self.caller.get_first_revision()
        rev2 = self.caller.get_second_revision()
        
        from rabbitvcs.ui.diff import SVNDiff
        self.action = VCSAction(
            self.vcs_client,
            notification=False
        )
        self.action.append(
            SVNDiff,
            url2,
            rev2,
            url1,
            rev1,
            sidebyside=True
        )
        self.action.start()

class ChangesContextMenu:
    """
    Defines context menu items for a table with files
    
    """
    def __init__(self, caller, event):
        """    
        @param  caller: The calling object
        @type   caller: object
        
        """        
        self.caller = caller
        self.event = event
        self.vcs_client = rabbitvcs.vcs.create_vcs_instance()

        self.conditions = ChangesContextMenuConditions(
            self.caller,
            self.vcs_client
        )
        
        self.callbacks = ChangesContextMenuCallbacks(
            self.caller,
            self.vcs_client
        )

        # The first element of each tuple is a key that matches a
        # ContextMenuItems item.  The second element is either None when there
        # is no submenu, or a recursive list of tuples for desired submenus.
        self.structure = [
            (MenuOpenFirst, None),
            (MenuOpenSecond, None),
            (MenuViewDiff, None),
            (MenuCompare, None)
        ]
        
    def show(self):
        if len(self.caller.selected_rows) == 0:
            return
            
        context_menu = GtkContextMenu(self.structure, self.conditions, self.callbacks)
        context_menu.show(self.event)


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main(
        usage="Usage: rabbitvcs changes [url1@rev1] [url2@rev2]"
    )
    
    pathrev1 = rabbitvcs.util.helper.parse_path_revision_string(args.pop(0))
    pathrev2 = (None, None)
    if len(args) > 0:
        pathrev2 = rabbitvcs.util.helper.parse_path_revision_string(args.pop(0))

    window = Changes(pathrev1[0], pathrev1[1], pathrev2[0], pathrev2[1])
    window.register_gtk_quit()
    gtk.main()
