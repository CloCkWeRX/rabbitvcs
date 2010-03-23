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

"""

UI layer.

"""

import os

import pygtk
import gobject
import gtk
import gtk.glade

from rabbitvcs import APP_NAME, LOCALE_DIR

REVISION_OPT = (["-r", "--revision"], {"help":"specify the revision number"})
BASEDIR_OPT = (["-b", "--base-dir"], {})
QUIET_OPT = (["-q", "--quiet"], {
    "help":     "Run the add command quietly, with no UI.", 
    "action":   "store_true", 
    "default":  False
})

#: Maps statuses to emblems.
#: TODO: should probably be possible to create this dynamically
STATUS_EMBLEMS = {
    "added" :       "rabbitvcs-added",
    "deleted":      "rabbitvcs-deleted",
    "removed":      "rabbitvcs-deleted",
    "modified":     "rabbitvcs-modified",
    "conflicted":   "rabbitvcs-conflicted",
    "missing":      "rabbitvcs-conflicted",
    "normal":       "rabbitvcs-normal",
    "clean":        "rabbitvcs-normal",
    "ignored":      "rabbitvcs-ignored",
    "locked":       "rabbitvcs-locked",
    "read_only":    "rabbitvcs-read_only",
    "obstructed":   "rabbitvcs-obstructed",
    "incomplete":   "rabbitvcs-incomplete",
    "unversioned":  "rabbitvcs-unversioned",
    "unknown":      "rabbitvcs-unknown",
    "calculating":  "rabbitvcs-calculating",
    "error":        "rabbitvcs-error"
}

def get_glade_tree(filename, id):
        path = "%s/glade/%s.glade" % (
            os.path.dirname(os.path.realpath(__file__)), 
            filename
        )
        gtk.glade.bindtextdomain(APP_NAME, LOCALE_DIR)
        gtk.glade.textdomain(APP_NAME)
        tree = gtk.glade.XML(path, id, APP_NAME)
        return tree

class GladeWidgetWrapper:
    
    def __init__(self, glade_filename = None, glade_id = None):
        if glade_filename:
            self.glade_filename = glade_filename
        
        if glade_id:
            self.glade_id = glade_id
            
        self.tree = get_glade_tree(self.glade_filename, self.glade_id)
        self.tree.signal_autoconnect(self)
    
    def get_widget(self, id = None):
        if not id:
            id = self.glade_id
        
        return self.tree.get_widget(id)

class InterfaceView(GladeWidgetWrapper):
    """
    Every ui window should inherit this class and send it the "self"
    variable, the glade filename (without the extension), and the id of the
    main window widget.
    
    When calling from the __main__ area (i.e. a window is opened via CLI,
    call the register_gtk_quit method to make sure the main app quits when
    the app is destroyed or finished.
    
    """
    
    def __init__(self, *args, **kwargs):
        GladeWidgetWrapper.__init__(self, *args, **kwargs)
        self.do_gtk_quit = False
        
        
    def hide(self):
        self.get_widget(self.glade_id).set_property('visible', False)
        
    def show(self):
        self.get_widget(self.glade_id).set_property('visible', True)
    
    def destroy(self):
        window = self.get_widget(self.glade_id)
        if window is not None:
            window.destroy()
    
    def close(self):
        self.destroy()
        if self.do_gtk_quit:
            gtk.main_quit()
            
    def register_gtk_quit(self):
        window = self.get_widget(self.glade_id)
        self.do_gtk_quit = True
        
        # This means we've already been closed
        if window is None:
            gobject.idle_add(gtk.main_quit)
    
    def gtk_quit_is_set(self):
        return self.do_gtk_quit
        
class InterfaceNonView:
    """
    Provides a way for an interface to handle quitting, etc without having
    to have a visible interface.
    
    """
    
    def __init__(self):
        self.do_gtk_quit = False

    def close(self):
        if self.do_gtk_quit:
            gtk.main_quit()
            
    def register_gtk_quit(self):
        self.do_gtk_quit = True
    
    def gtk_quit_is_set(self):
        return self.do_gtk_quit

def main(allowed_options=None, description=None, usage=None):
    from os import getcwd
    from sys import argv
    from optparse import OptionParser
    from rabbitvcs.util.helper import get_common_directory
    
    parser = OptionParser(usage=usage, description=description)
    
    if allowed_options:
        for (option_args, option_kwargs) in allowed_options:
            parser.add_option(*option_args, **option_kwargs)
        
    (options, args) = parser.parse_args(argv)
    
    # Convert "." to current working directory
    paths = args[1:]
    for i in range(0, len(paths)):
        if paths[i] == ".":
            paths[i] = getcwd()
        
    if not paths:
        paths = [getcwd()]
        
    if parser.has_option("--base-dir") and not options.base_dir: 
        options.base_dir = get_common_directory(paths)
        
    return (options, paths)
