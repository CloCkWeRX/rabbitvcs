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
import thread

import pygtk
import gobject
import gtk
from datetime import datetime

from rabbitvcs.ui import InterfaceView
from rabbitvcs.lib.contextmenu import GtkContextMenu, GtkFilesContextMenuConditions, \
    GtkFilesContextMenuCallbacks, ContextMenuItems, GtkContextMenuCaller
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.lib.helper
import rabbitvcs.lib.vcs
from rabbitvcs.lib.log import Log
from rabbitvcs.lib.decorators import gtk_unsafe

log = Log("rabbitvcs.ui.add")

from rabbitvcs import gettext
_ = gettext.gettext

gtk.gdk.threads_init()

class Browser(InterfaceView, GtkContextMenuCaller):
    def __init__(self, url):
        InterfaceView.__init__(self, "browser", "Browser")

        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        self.url = self.vcs.get_repo_url(url)

        self.urls = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("urls"), 
            rabbitvcs.lib.helper.get_repository_paths()
        )
        if self.url:
            self.urls.set_child_text(self.url)

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.vcs,
            url_combobox=self.urls
        )

        self.items = []
        self.list_table = rabbitvcs.ui.widget.Table(
            self.get_widget("list"), 
            [rabbitvcs.ui.widget.TYPE_PATH, gobject.TYPE_INT, 
                gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_FLOAT], 
            [_("Path"), _("Revision"), _("Size"), _("Author"), _("Date")],
            filters=[{
                "callback": self.file_filter,
                "user_data": {
                    "column": 0
                }
            },{
                "callback": self.revision_filter,
                "user_data": {
                    "column": 1
                }
            },{
                "callback": self.size_filter,
                "user_data": {
                    "column": 2
                }
            },{
                "callback": self.date_filter,
                "user_data": {
                    "column": 4
                }
            }],
            filter_types=[gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING], 
            callbacks={
                "file-column-callback": self.file_column_callback,
                "row-activated": self.on_row_activated,
                "mouse-event":   self.on_list_table_mouse_event
            }
        )
        
        self.clipboard = None
        self.url_clipboard = gtk.Clipboard()
        self.repo_root_url = None

        if url:
            self.load()

    def load(self):
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            notification=False
        )
        revision = self.revision_selector.get_revision_object()
        self.action.append(self.vcs.list, self.urls.get_active_text(), 
            revision=revision, recurse=False)
        self.action.append(self.init_repo_root_url)
        self.action.append(self.populate_table, 0)
        self.action.start()

    @gtk_unsafe
    def populate_table(self, item_index=0):
        self.list_table.clear()
        self.items = self.action.get_result(item_index)
        self.items.sort(self.sort_files)
        
        self.list_table.append(["..", 0, 0, "", 0])
        for item,locked in self.items[1:]:
            self.list_table.append([
                item.path,
                item.created_rev.number,
                item.size,
                item.last_author,
                item.time
            ])
    
    def init_repo_root_url(self):
        if self.repo_root_url is None:
            self.repo_root_url = self.vcs.get_repo_root_url(self.url)
    
    def on_destroy(self, widget):
        self.close()
    
    def on_close_clicked(self, widget):
        self.close()

    def on_refresh_clicked(self, widget):
        self.load()

    def on_row_activated(self, treeview, data, col):
        path = self.list_table.get_selected_row_items(0)[0]
        if path == "..":
            path = self.url.split("/")[0:-1]
            self.url = "/".join(path)
        else:
            self.url = path

        self.urls.set_child_text(self.url)
        self.load()

    def file_column_callback(self, filename):
        """
        Determine the node kind (dir or file) from our retrieved items list
        """

        if filename == "..":
            return "dir"

        for item,locked in self.items:
            if item.path == filename:
                return self.vcs.NODE_KINDS_REVERSE[item.kind]
        return None

    def sort_files(self, x, y):
        """
        Sort the browser listing so that folders are on top and then sort
        alphabetically.

        """
        xkind = self.vcs.NODE_KINDS_REVERSE[x[0].kind]
        ykind = self.vcs.NODE_KINDS_REVERSE[y[0].kind]
        if xkind == "dir" and ykind == "dir":
            return cmp(x[0].repos_path, y[0].repos_path)
        elif xkind == "dir" and ykind == "file":
            return -1
        else:
            return 1

    def file_filter(self, row, column, user_data=None):
        """
        Table filter to just show the basename of the item path
        """

        if row[column]:
            return os.path.basename(row[column])
            
        return row[column]

    def size_filter(self, row, column, user_data=None):
        """
        Table filter to convert the item size to a "pretty" filesize
        """

        if self.file_column_callback(row[0]) == "file":
            return rabbitvcs.lib.helper.pretty_filesize(row[column])

        return ""

    def revision_filter(self, row, column, user_data=None):
        """
        Table filter to convert revision to a desired format
        """
        
        if row[0] == "..":
            return ""
        
        return row[column]

    def date_filter(self, row, column, user_data=None):
        """
        Table filter to convert the item date to something readable
        """
        
        if row[0] == "..":
            return ""
        
        if row[column]:
            change_time = datetime.fromtimestamp(row[column])
            return change_time.strftime("%Y-%m-%d %H:%M:%S")
        
        return str(row[column])

    def on_list_table_mouse_event(self, treeview, data=None):
        if data is not None and data.button == 3:
            self.show_list_table_popup_menu(treeview, data)

    def show_list_table_popup_menu(self, treeview, data):
        paths = self.list_table.get_selected_row_items(0)
        if len(paths) == 0:
            paths.append(self.url)
        
        BrowserContextMenu(self, data, None, self.vcs, paths).show()

    def update_clipboard(self, action, urls):
        self.clipboard = {
            "action": action,
            "urls": urls
        }

    def clipboard_has_cut(self):
        return (self.clipboard is not None and self.clipboard["action"] == "cut")

    def clipboard_has_copy(self):
        return (self.clipboard is not None and self.clipboard["action"] == "cut")

    def empty_clipboard(self):
        self.clipboard = None
    
    def set_url_clipboard(self, url):
        self.url_clipboard.set_text(url)
    
    def get_repo_root_url(self):
        return self.repo_root_url

    def get_url(self):
        return self.urls.get_active_text()

class BrowserDialog(Browser):
    def __init__(self, path, callback=None):
        """
        Override the normal Browser class so that we can hide the window as we need.
        Also, provide a callback for when the close button is clicked so that we
        can get some desired data.
        """
        Browser.__init__(self, path)
        self.callback = callback
        
    def on_destroy(self, widget):
        pass
    
    def on_close_clicked(self, widget, data=None):
        self.hide()
        if self.callback is not None:
            path = self.urls.get_active_text()
            selected = self.list_table.get_selected_row_items(0)
            if len(selected) > 0:
                path = selected
            self.callback(path)

class BrowserContextMenuConditions(GtkFilesContextMenuConditions):
    def __init__(self, vcs_client, paths, caller):
        GtkFilesContextMenuConditions.__init__(self, vcs_client, paths)
        self.caller = caller

    def _open(self, data1=None, data2=None):
        return True
    
    def show_log(self, data1=None, data2=None):
        return True
    
    def annotate(self, data1=None, data2=None):
        return True
    
    def checkout(self, data1=None, data2=None):
        return True
    
    def export(self, data1=None, data2=None):
        return True
        
    def rename(self, data1=None):
        revision = self.caller.revision_selector.get_revision_object()
        return (revision.kind == "head")
    
    def delete(self, data1=None, data2=None):
        revision = self.caller.revision_selector.get_revision_object()
        return (revision.kind == "head")

    def create_folder(self, data1=None):
        if self.path_dict["length"] == 1:
            return (self.caller.file_column_callback(self.paths[0]) == "dir")

        return (self.path_dict["length"] == 0)

    def cut_to_clipboard(self, data1=None, data2=None):
        return True

    def copy_to_clipboard(self, data1=None, data2=None):
        return True

    def paste_from_clipboard(self, data1=None):
        return (self.caller.clipboard_has_cut() or self.caller.clipboard_has_copy())

    def copy_to(self, data1=None, data2=None):
        return True

    def copy_url_to_clipboard(self, data1=None, data2=None):
        return (self.path_dict["length"] == 1)

    def move_to(self, data1=None, data2=None):
        return True

class BrowserContextMenuCallbacks(GtkFilesContextMenuCallbacks):
    def __init__(self, caller, base_dir, vcs_client, paths=[]):
        self.caller = caller
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        self.paths = paths

    def __update_browser_url(self, url):
        # Make sure the Browser variables are updated with the new path
        self.caller.urls.set_child_text(url)
        self.caller.url = url

    def __get_browser_revision(self):
        return self.caller.revision_selector.get_revision_object()

    def _open(self, data=None, user_data=None):
        self.caller.action = rabbitvcs.ui.action.VCSAction(
            self.vcs_client,
            notification=False
        )
        
        exported_paths = []
        for path in self.paths:
            export_path = "/tmp/" + os.path.basename(self.paths[0])
            exported_paths.append(export_path)
            self.caller.action.append(self.vcs_client.export, self.paths[0], 
                export_path, revision=self.__get_browser_revision())

        for path in exported_paths:
            self.caller.action.append(rabbitvcs.lib.helper.open_item, path)

        self.caller.action.start()
    
    def show_log(self, data=None, user_data=None):
        rabbitvcs.lib.helper.launch_ui_window("log", [self.paths[0]])
    
    def annotate(self, data=None):
        return True
    
    def checkout(self, data=None):
        return True
    
    def export(self, data=None):
        return True
        
    def rename(self, data=None, user_data=None):
        (base, filename) = os.path.split(self.paths[0])
    
        from rabbitvcs.ui.dialog import OneLineTextChange
        dialog = OneLineTextChange(_("Rename"), _("New Name:"), filename)
        (result, new_name) = dialog.run()
        
        if result == gtk.RESPONSE_CANCEL:
            return
        
        new_url = base.rstrip("/") + "/" + new_name
        path_to_refresh = self.caller.get_url()
        if self.paths[0] == path_to_refresh:
            path_to_refresh = new_url
            self.__update_browser_url(path_to_refresh)

        self.caller.action = rabbitvcs.ui.action.VCSAction(
            self.vcs_client,
            notification=False
        )
        self.caller.action.append(self.vcs_client.move, self.paths[0], new_url)
        self.caller.action.append(self.vcs_client.list, path_to_refresh, recurse=False)
        self.caller.action.append(self.caller.populate_table, 1)
        self.caller.action.start()
    
    def delete(self, data=None, user_data=None):
        path_to_refresh = self.caller.get_url() 
        if self.paths[0] == path_to_refresh:            
            # If the deleted path is the same as the current path, go to the parent
            path_to_refresh = path_to_refresh.split("/")[0:-1]
            path_to_refresh = "/".join(path_to_refresh)
        
            self.__update_browser_url(path_to_refresh)
        
        self.caller.action = rabbitvcs.ui.action.VCSAction(
            self.vcs_client,
            notification=False
        )
        self.caller.action.append(self.vcs_client.remove, self.paths[0])
        self.caller.action.append(self.vcs_client.list, path_to_refresh, recurse=False)
        self.caller.action.append(self.caller.populate_table, 1)
        self.caller.action.start()  

    def create_folder(self, data=None, user_data=None):
        from rabbitvcs.ui.dialog import NewFolder
        dialog = NewFolder()
        result = dialog.run()
        if result is None:
            return
            
        (folder_name, log_message) = result
        new_url = self.paths[0].rstrip("/") + "/" + folder_name

        self.caller.action = rabbitvcs.ui.action.VCSAction(
            self.vcs_client,
            notification=False
        )
        self.caller.action.append(self.vcs_client.mkdir, new_url, log_message)
        self.caller.action.append(self.vcs_client.list, self.paths[0], recurse=False)
        self.caller.action.append(self.caller.populate_table, 1)
        self.caller.action.start()        

    def cut_to_clipboard(self, data=None, user_data=None):
        self.caller.update_clipboard("cut", self.paths)

    def copy_to_clipboard(self, data=None, user_data=None):
        self.caller.update_clipboard("copy", self.paths)

    def paste_from_clipboard(self, data=None, user_data=None):
        self.caller.empty_clipboard()

    def copy_to(self, data=None):
        pass

    def copy_url_to_clipboard(self, data=None, user_data=None):
        self.caller.set_url_clipboard(self.paths[0])

    def move_to(self, data=None):
        pass

class BrowserContextMenu:
    def __init__(self, caller, event, base_dir, vcs_client, paths=[]):
        
        self.caller = caller
        self.event = event
        self.paths = paths
        self.base_dir = base_dir
        self.vcs_client = vcs_client
        
        self.conditions = BrowserContextMenuConditions(
            self.vcs_client, 
            paths,
            self.caller
        )
        self.callbacks = BrowserContextMenuCallbacks(
            self.caller, 
            self.base_dir,
            self.vcs_client, 
            paths
        )
        
        self.structure = [
            ("Open", None),
            ("Separator0", None),
            ("Show_Log", None),
            ("Annotate", None),
            ("Export", None),
            ("Checkout", None),
            ("Separator1", None),
            ("CreateRepoFolder", None),
            ("Separator2", None),
            ("CutToClipboard", None),
            ("CopyToClipboard", None),
            ("PasteFromClipboard", None),
            ("Separator3", None),
            ("Rename", None),
            ("Delete", None),
            ("CopyTo", None),
            ("CopyUrlToClipboard", None),
            ("MoveTo", None)
        ]

        items_to_append = {
            "CreateRepoFolder": {
                "label": _("Create folder..."),
                "icon": gtk.STOCK_NEW,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.create_folder, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.create_folder
                }
            },
            "CutToClipboard": {
                "label": _("Cut"),
                "icon": gtk.STOCK_CUT,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.cut_to_clipboard, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.cut_to_clipboard
                }
            },
            "CopyToClipboard": {
                "label": _("Copy"),
                "icon": gtk.STOCK_COPY,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.copy_to_clipboard, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.copy_to_clipboard
                }
            },
            "PasteFromClipboard": {
                "label": _("Paste"),
                "icon": gtk.STOCK_PASTE,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.paste_from_clipboard, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.paste_from_clipboard
                }
            },
            "CopyTo": {
                "label": _("Copy To..."),
                "icon": gtk.STOCK_COPY,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.copy_to, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.copy_to
                }
            },
            "CopyUrlToClipboard": {
                "label": _("Copy URL to clipboard"),
                "icon": "rabbitvcs-diff",
                "signals": {
                    "activate": {
                        "callback": self.callbacks.copy_url_to_clipboard, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.copy_url_to_clipboard
                }
            },
            "MoveTo": {
                "label": _("Move to..."),
                "icon": gtk.STOCK_SAVE_AS,
                "signals": {
                    "activate": {
                        "callback": self.callbacks.move_to, 
                        "args": None
                    }
                },
                "condition": {
                    "callback": self.conditions.move_to
                }
            }
        }
        
        self.items = ContextMenuItems(self.conditions, self.callbacks, items_to_append).get_items()

    def show(self):
        context_menu = GtkContextMenu(self.structure, self.items)
        context_menu.show(self.event)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, url) = main(
        usage="Usage: rabbitvcs browser [url]"
    )

    window = Browser(url[0])
    window.register_gtk_quit()
    gtk.main()
