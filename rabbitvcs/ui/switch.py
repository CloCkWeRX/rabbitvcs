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

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.log import LogDialog
from rabbitvcs.ui.action import VCSAction
import rabbitvcs.ui.widget
import rabbitvcs.ui.dialog
import rabbitvcs.lib.helper

from rabbitvcs import gettext
_ = gettext.gettext

class Switch(InterfaceView):
    def __init__(self, path, revision=None):
        InterfaceView.__init__(self, "switch", "Switch")

        self.path = path
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        
        self.get_widget("path").set_text(self.path)
        self.repositories = rabbitvcs.ui.widget.ComboBox(
            self.get_widget("repositories"), 
            rabbitvcs.lib.helper.get_repository_paths()
        )

        self.revision_selector = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("revision_container"),
            self.vcs,
            revision=revision,
            url_combobox=self.repositories,
            expand=True
        )
        
        self.repositories.set_child_text(self.vcs.get_repo_url(self.path))

    def on_destroy(self, widget):
        self.close()

    def on_cancel_clicked(self, widget):
        self.close()

    def on_ok_clicked(self, widget):
        url = self.repositories.get_active_text()
        
        if not url or not self.path:
            rabbitvcs.ui.dialog.MessageBox(_("The repository location is a required field."))
            return

        revision = self.revision_selector.get_revision_object()
        self.hide()
        self.action = rabbitvcs.ui.action.VCSAction(
            self.vcs,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(self.action.set_header, _("Switch"))
        self.action.append(self.action.set_status, _("Running Switch Command..."))
        self.action.append(rabbitvcs.lib.helper.save_repository_path, url)
        self.action.append(
            self.vcs.switch,
            self.path,
            url,
            revision=revision
        )
        self.action.append(self.action.set_status, _("Completed Switch"))
        self.action.append(self.action.finish)
        self.action.start()


if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main()
            
    window = Switch(args[0], revision=options.revision)
    window.register_gtk_quit()
    gtk.main()
