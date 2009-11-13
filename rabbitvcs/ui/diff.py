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
import os
import tempfile

from rabbitvcs import TEMP_DIR_PREFIX
from rabbitvcs.ui import InterfaceNonView
from rabbitvcs.lib.vcs import create_vcs_instance
import rabbitvcs.lib.helper

from rabbitvcs import gettext
_ = gettext.gettext

class Diff(InterfaceNonView):
    def __init__(self, path1, revision1=None, path2=None, revision2=None, 
            side_by_side=False):
        InterfaceNonView.__init__(self)

        self.vcs = create_vcs_instance()

        self.path1 = path1
        self.path2 = path2
        self.side_by_side = side_by_side
        self.revision1 = self.get_revision_object(revision1, "base")
        self.revision2 = self.get_revision_object(revision2, "head")
        
        self.temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX)

        if path2 is None:
            self.path2 = path1

    def get_revision_object(self, value, default):
        # If value is a rabbitvcs Revision object, return it
        if hasattr(value, "is_revision_object"):
            return value
        
        # If value is None, use the default
        if value is None:
            return self.vcs.revision(default)          

        # If the value is an integer number, return a numerical revision object
        # otherwise, a string revision value has been passed, use that as "kind"
        try:
            value = int(value)
            return self.vcs.revision("number", value)
        except ValueError:
            # triggered when passed a string
            return self.vcs.revision(value)
                
    def launch(self):
        if self.side_by_side:
            self.launch_side_by_side_diff()
        else:
            self.launch_unified_diff()
    
    def launch_unified_diff(self):
        """
        Launch diff as a unified diff in a text editor or .diff viewer
        
        """
        diff_text = self.vcs.diff(
            self.temp_dir,
            self.path1,
            self.revision1,
            self.path2,
            self.revision2
        )
        
        fh = tempfile.mkstemp("-rabbitvcs-" + str(self.revision1) + "-" + str(self.revision2) + ".diff")
        os.write(fh[0], diff_text)
        os.close(fh[0])
        rabbitvcs.lib.helper.open_item(fh[1])
        
    def launch_side_by_side_diff(self):
        """
        Launch diff as a side-by-side comparison using our comparison tool
        
        """        
        if os.path.exists(self.path1):
            dest1 = self.path1
        else:
            dest1 = "/tmp/rabbitvcs-1-" + str(self.revision1) + "-" + os.path.basename(self.path1)          
            self.vcs.export(self.path1, dest1, self.revision1)
    
        if os.path.exists(self.path2):
            dest2 = self.path2
        else:
            dest2 = "/tmp/rabbitvcs-2-" + str(self.revision2) + "-" + os.path.basename(self.path2)
            self.vcs.export(self.path2, dest2, self.revision2)
    
        rabbitvcs.lib.helper.launch_diff_tool(dest1, dest2)

class SVNDiff(Diff):
    def __init__(self, path1, revision1=None, path2=None, revision2=None,
            side_by_side=False):
        Diff.__init__(self, path1, revision1, path2, revision2, side_by_side)

        self.launch()

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main([
        (["-s", "--sidebyside"], {
            "help":     _("View diff as side-by-side comparison"), 
            "action":   "store_true", 
            "default":  False
        })],
        usage="Usage: rabbitvcs diff [url1@rev1] [url2@rev2]"
    )
    
    pathrev1 = rabbitvcs.lib.helper.parse_path_revision_string(args.pop(0))
    pathrev2 = (None, None)
    if len(args) > 0:
        pathrev2 = rabbitvcs.lib.helper.parse_path_revision_string(args.pop(0))

    SVNDiff(pathrev1[0], pathrev1[1], pathrev2[0], pathrev2[1], sidebyside=sidebyside)
