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

import os.path
import thread

import pygtk
import gobject
import gtk
from datetime import datetime

from rabbitvcs.ui import InterfaceView
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.ui.action
import rabbitvcs.util.helper
import rabbitvcs.vcs

from rabbitvcs import gettext
_ = gettext.gettext

DATETIME_FORMAT = rabbitvcs.util.helper.DT_FORMAT_THISWEEK

gtk.gdk.threads_init()

class Push(InterfaceView):
    def __init__(self, path):
        InterfaceView.__init__(self, "push", "Push")
        
        self.path = path
        self.vcs = rabbitvcs.vcs.VCS()

    #
    # Event handlers
    #
    
    def on_destroy(self, widget):
        self.destroy()
        
    def on_cancel_clicked(self, widget, data=None):
        self.close()
    
    def on_ok_clicked(self, widget, data=None):
        pass

class GitPush(Push):
    def __init__(self, path):
        Push.__init__(self, path)

        self.git = self.vcs.git(path)
        
        self.repository_selector = rabbitvcs.ui.widget.GitRepositorySelector(
            self.get_widget("repository_container"),
            self.git
        )

        self.log_table = rabbitvcs.ui.widget.Table(
            self.get_widget("log"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Date"), _("Message")],
            flags={
                "sortable": True, 
                "sort_on": 0
            }
        )
        
        self.initialize_logs()

    def on_ok_clicked(self, widget, data=None):
        self.hide()
    
        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()
        
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        self.action.append(self.action.set_header, _("Push"))
        self.action.append(self.action.set_status, _("Running Push Command..."))
        self.action.append(self.git.push, repository, branch)
        self.action.append(self.action.set_status, _("Completed Push"))
        self.action.append(self.action.finish)
        self.action.start()

    def initialize_logs(self):
        """
        Initializes the git logs
        """
        
        try:
            thread.start_new_thread(self.load_logs, ())
        except Exception, e:
            log.exception(e)

    def load_logs(self):
        gtk.gdk.threads_enter()
        self.get_widget("status").set_text(_("Loading..."))

        gtk.gdk.threads_leave()

        self.load_local_log()
        self.load_remote_log()

        gtk.gdk.threads_enter()
        self.get_widget("status").set_text("")
        self.update_widgets()
        gtk.gdk.threads_leave()

    def load_local_log(self):
        self.local_log = self.git.log(limit=10, showtype="branch")
        
    def load_remote_log(self):
        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()

        refspec = "refs/remotes/%s/%s" % (repository, branch)
        self.remote_log = self.git.log(revision=self.git.revision(refspec), limit=10, showtype="branch")

    def update_widgets(self):
        repository = self.repository_selector.repository_opt.get_active_text()
        branch = self.repository_selector.branch_opt.get_active_text()

        if not repository or not branch:
            self.get_widget("ok").set_sensitive(False)
            return

        has_commits = False
        for item in self.local_log:
            try:
                remote_log_item = self.remote_log[0]
                if unicode(remote_log_item.revision) != unicode(item.revision):
                    self.log_table.append([
                        rabbitvcs.util.helper.format_datetime(item.date),
                        rabbitvcs.util.helper.format_long_text(item.message.rstrip("\n"))
                    ])
                    has_commits = True
                else:
                    break

            except IndexError:
                break

        if not has_commits:
            self.get_widget("ok").set_sensitive(False)
            self.get_widget("status").set_text(_("No commits found"))

classes_map = {
    rabbitvcs.vcs.VCS_GIT: GitPush
}

def push_factory(path):
    guess = rabbitvcs.vcs.guess(path)
    return classes_map[guess["vcs"]](path)
    
if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(
        usage="Usage: rabbitvcs push [path]"
    )

    window = push_factory(paths[0])
    window.register_gtk_quit()
    gtk.main()
