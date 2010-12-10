#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2010 by Adam Plumb <adamplumb@gmail.com>
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

from rabbitvcs.ui import InterfaceNonView, InterfaceView
from rabbitvcs.ui.action import SVNAction, GitAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog

from rabbitvcs import gettext
_ = gettext.gettext

class SVNUpdate(InterfaceNonView):
    """
    This class provides an interface to generate an "update".
    Pass it a path and it will start an update, running the notification dialog.  
    There is no glade .
    
    """

    def __init__(self, paths):
        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()

    def start(self):
        self.action = SVNAction(
            self.svn,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Update"))
        self.action.append(self.action.set_status, _("Updating..."))
        self.action.append(self.svn.update, self.paths)
        self.action.append(self.action.set_status, _("Completed Update"))
        self.action.append(self.action.finish)
        self.action.start()

class GitUpdate(InterfaceView):
    """
    This class provides an interface to generate an "update".
    Pass it a path and it will start an update, running the notification dialog.  
    There is no glade .
    
    """

    def __init__(self, paths):
        InterfaceView.__init__(self, "git-update", "Update")

        self.paths = paths
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(paths[0])

        self.repository_selector = rabbitvcs.ui.widget.GitRepositorySelector(
            self.get_widget("repository_container"),
            self.git
        )

    def on_destroy(self, widget):
        self.destroy()
        
    def on_cancel_clicked(self, widget, data=None):
        self.close()

    def on_ok_clicked(self, widget, data=None):
        self.hide()
        merge = self.get_widget("merge").get_active()

        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()
    
        self.action = GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Update"))
        self.action.append(self.action.set_status, _("Updating..."))
        if merge:
            self.action.append(self.git.pull, repository, branch)
        else:
            self.action.append(self.git.fetch, repository, branch)
        self.action.append(self.action.set_status, _("Completed Update"))
        self.action.append(self.action.finish)
        self.action.start()

classes_map = {
    rabbitvcs.vcs.VCS_SVN: SVNUpdate, 
    rabbitvcs.vcs.VCS_GIT: GitUpdate
}

def update_factory(paths):
    guess = rabbitvcs.vcs.guess(paths[0])
    return classes_map[guess["vcs"]](paths)

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs update [path1] [path2] ...")

    window = update_factory(paths)
    window.register_gtk_quit()
    if isinstance(window, SVNUpdate):
        window.start()
    gtk.main()
