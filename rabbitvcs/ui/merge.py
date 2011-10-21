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

import cgi

import pygtk
import gobject
import gtk

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.log import SVNLogDialog
from rabbitvcs.ui.action import SVNAction
import rabbitvcs.vcs
import rabbitvcs.ui.widget
import rabbitvcs.util.helper

from rabbitvcs import gettext
_ = gettext.gettext

class SVNMerge(InterfaceView):
    def __init__(self, path):
        InterfaceView.__init__(self, "merge", "Merge")
        
        
        self.assistant = self.get_widget("Merge")
        
        self.path = path
        
        self.page = self.assistant.get_nth_page(0)
        self.last_page = None
        
        self.vcs = rabbitvcs.vcs.VCS()
        self.svn = self.vcs.svn()
        
        if not self.svn.has_merge2():
            self.get_widget("mergetype_range_opt").set_sensitive(False)
            self.get_widget("mergetype_tree_opt").set_active(True)
            self.get_widget("mergetype_reintegrate_opt").set_active(False) 
            self.get_widget("mergeoptions_only_record").set_active(False)

        if not self.svn.has_merge_reintegrate():
            self.get_widget("mergetype_reintegrate_opt").set_sensitive(False)

        self.assistant.set_page_complete(self.page, True)
        self.assistant.set_forward_page_func(self.on_forward_clicked)
        
        self.repo_paths = rabbitvcs.util.helper.get_repository_paths()
        
        # Keeps track of which stages should be marked as complete
        self.type = None
    #
    # Assistant UI Signal Callbacks
    #

    def on_destroy(self, widget):
        self.destroy()
    
    def on_cancel_clicked(self, widget):
        self.close()
    
    def on_close_clicked(self, widget):
        self.close()

    def on_apply_clicked(self, widget):
        self.merge()
    
    def on_test_clicked(self, widget):
        self.merge(test=True)            

    def merge(self, test=False):
        if self.type is None:
            return
        
        if test:
            startcmd = _("Running Merge Test")
            endcmd = _("Completed Merge Test")
        else:
            startcmd = _("Running Merge Command")
            endcmd = _("Completed Merge")
            self.hide()

        recursive = self.get_widget("mergeoptions_recursive").get_active()
        ignore_ancestry = self.get_widget("mergeoptions_ignore_ancestry").get_active()
        
        record_only = False
        if self.svn.has_merge2():
            record_only = self.get_widget("mergeoptions_only_record").get_active()

        action = SVNAction(self.svn, register_gtk_quit=(not test))
        action.append(action.set_header, _("Merge"))
        action.append(action.set_status, startcmd)
        
        args = ()
        kwargs = {}
        
        if self.type == "range":
            url = self.get_widget("mergerange_from_urls").get_active_text()
            head_revision = self.svn.get_head(self.path)
            revisions = self.get_widget("mergerange_revisions").get_text()
            if revisions == "":
                revisions = "head"
            revisions = revisions.lower().replace("head", str(head_revision))

            ranges = []
            for r in revisions.split(","):
                if r.find("-") != -1:
                    (low, high) = r.split("-")
                elif r.find(":") != -1:
                    (low, high) = r.split(":")
                else:
                    low = r
                    high = r

                # Before pysvn v1.6.3, there was a bug that required the ranges 
                # tuple to have three elements, even though only two were used
                # Fixed in Pysvn Revision 1114
                if (self.svn.interface == "pysvn" and self.svn.is_version_less_than((1,6,3,0))):
                    ranges.append((
                        self.svn.revision("number", number=int(low)).primitive(),
                        self.svn.revision("number", number=int(high)).primitive(),
                        None
                    ))
                else:
                    ranges.append((
                        self.svn.revision("number", number=int(low)).primitive(),
                        self.svn.revision("number", number=int(high)).primitive(),
                    ))

            action.append(rabbitvcs.util.helper.save_repository_path, url)
            
            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (
                self.svn.merge_ranges,
                url,
                ranges,
                self.svn.revision("head"),
                self.path
            )
            kwargs = {
                "notice_ancestry": (not ignore_ancestry),
                "dry_run":          test
            }
            if record_only:
                kwargs["record_only"] = record_only

        elif self.type == "reintegrate":
            url = self.merge_reintegrate_repos.get_active_text()
            revision = self.merge_reintegrate_revision.get_revision_object()

            action.append(rabbitvcs.util.helper.save_repository_path, url)
            
            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (
                self.svn.merge_reintegrate,
                url,
                revision,
                self.path
            )
            kwargs = {
                "dry_run":          test
            }

        elif self.type == "tree":
            from_url = self.get_widget("mergetree_from_urls").get_active_text()
            from_revision = self.svn.revision("head")
            if self.get_widget("mergetree_from_revision_number_opt").get_active():
                from_revision = self.svn.revision(
                    "number",
                    number=int(self.get_widget("mergetree_from_revision_number").get_text())
                )
            to_url = self.get_widget("mergetree_to_urls").get_active_text()
            to_revision = self.svn.revision("head")
            if self.get_widget("mergetree_to_revision_number_opt").get_active():
                to_revision = self.svn.revision(
                    "number",
                    number=int(self.get_widget("mergetree_to_revision_number").get_text())
                )

            action.append(rabbitvcs.util.helper.save_repository_path, from_url)
            action.append(rabbitvcs.util.helper.save_repository_path, to_url)

            # Build up args and kwargs because some args are not supported
            # with older versions of pysvn/svn
            args = (
                self.svn.merge_trees,
                from_url,
                from_revision,
                to_url,
                to_revision,
                self.path
            )
            kwargs = {
                "recurse": recursive
            }
        
        if len(args) > 0:
            action.append(*args, **kwargs) 
                       
        action.append(action.set_status, endcmd)
        action.append(action.finish)
        action.start()

    def on_prepare(self, widget, page):
        self.page = page
        
        current = self.assistant.get_current_page()
        if current == 1:
            self.on_mergerange_prepare()
        elif current == 2:
            self.on_merge_reintegrate_prepare()
        elif current == 3:
            self.on_mergetree_prepare()
        elif current == 4:
            self.on_mergeoptions_prepare()

        self.last_page = current

    def on_forward_clicked(self, widget):
        current = self.assistant.get_current_page()
        if current == 0:
            if self.get_widget("mergetype_range_opt").get_active():
                next = 1
                self.type = "range"
            elif self.get_widget("mergetype_reintegrate_opt").get_active():
                next = 2
                self.type = "reintegrate"
            elif self.get_widget("mergetype_tree_opt").get_active():
                next = 3
                self.type = "tree"
        else:
            next = 4
        
        return next

    #
    # Step 2a: Merge a Range of Revisions
    #
    
    def on_mergerange_prepare(self):
        if not hasattr(self, "mergerange_repos"):
            self.mergerange_repos = rabbitvcs.ui.widget.ComboBox(
                self.get_widget("mergerange_from_urls"), 
                self.repo_paths
            )
            self.get_widget("mergerange_working_copy").set_text(self.path)
        
        self.mergerange_check_ready()
        
    def on_mergerange_show_log1_clicked(self, widget):
        SVNLogDialog(
            self.get_widget("mergerange_from_urls").get_active_text(),
            ok_callback=self.on_mergerange_log1_closed, 
            multiple=True
        )
    
    def on_mergerange_log1_closed(self, data):
        self.get_widget("mergerange_revisions").set_text(data)

    def on_mergerange_from_urls_changed(self, widget):
        self.mergerange_check_ready()

    def on_mergerange_revisions_changed(self, widget):
        self.mergerange_check_ready()

    def mergerange_check_ready(self):
        ready = True
        if self.get_widget("mergerange_from_urls").get_active_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)

        allow_log = False
        if self.get_widget("mergerange_from_urls").get_active_text():
            allow_log = True        
        self.get_widget("mergerange_show_log1").set_sensitive(allow_log)

    #
    # Step 2b: Reintegrate a Branch
    #

    def on_merge_reintegrate_prepare(self):
        if not hasattr(self, "merge_reintegrate_repos"):
            self.merge_reintegrate_repos = rabbitvcs.ui.widget.ComboBox(
                self.get_widget("merge_reintegrate_repos"), 
                self.repo_paths
            )
            self.merge_reintegrate_repos.cb.connect("changed", self.on_merge_reintegrate_from_urls_changed)
            self.get_widget("merge_reintegrate_working_copy").set_text(self.path)

        if not hasattr(self, "merge_reintegrate_revision"):
            self.merge_reintegrate_revision = rabbitvcs.ui.widget.RevisionSelector(
                self.get_widget("revision_container"),
                self.svn,
                url_combobox=self.merge_reintegrate_repos,
                expand=True
            )

    def on_merge_reintegrate_browse_clicked(self, widget):
        from rabbitvcs.ui.browser import SVNBrowserDialog
        SVNBrowserDialog(self.path, callback=self.on_repo_chooser_closed)

    def on_repo_chooser_closed(self, new_url):
        self.merge_reintegrate_repos.set_child_text(new_url)
        self.merge_reintegrate_check_ready()
        
    def on_merge_reintegrate_from_urls_changed(self, widget):
        self.merge_reintegrate_check_ready()
    
    def merge_reintegrate_check_ready(self):
        ready = True
        if self.get_widget("merge_reintegrate_repos").get_active_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)

    #
    # Step 2c: Merge two different trees
    #
    
    def on_mergetree_prepare(self):
        if not hasattr(self, "mergetree_from_repos"):
            self.mergetree_from_repos = rabbitvcs.ui.widget.ComboBox(
                self.get_widget("mergetree_from_urls"), 
                self.repo_paths
            )
            self.mergetree_to_repos = rabbitvcs.ui.widget.ComboBox(
                self.get_widget("mergetree_to_urls"), 
                self.repo_paths
            )
            self.get_widget("mergetree_working_copy").set_text(self.path)

    def on_mergetree_from_show_log_clicked(self, widget):
        SVNLogDialog(
            self.path,
            ok_callback=self.on_mergetree_from_show_log_closed, 
            multiple=False
        )

    def on_mergetree_from_show_log_closed(self, data):
        self.get_widget("mergetree_from_revision_number").set_text(data)
        self.get_widget("mergetree_from_revision_number_opt").set_active(True)

    def on_mergetree_to_show_log_clicked(self, widget):
        SVNLogDialog(
            self.path,
            ok_callback=self.on_mergetree_to_show_log_closed, 
            multiple=False
        )

    def on_mergetree_to_show_log_closed(self, data):
        self.get_widget("mergetree_to_revision_number").set_text(data)
        self.get_widget("mergetree_to_revision_number_opt").set_active(True)

    def on_mergetree_working_copy_show_log_clicked(self, widget):
        SVNLogDialog(self.path)
        
    def on_mergetree_from_revision_number_focused(self, widget, data):
        self.get_widget("mergetree_from_revision_number_opt").set_active(True)

    def on_mergetree_to_revision_number_focused(self, widget, data):
        self.get_widget("mergetree_to_revision_number_opt").set_active(True)

    def on_mergetree_from_urls_changed(self, widget):
        self.mergetree_check_ready()

    def on_mergetree_to_urls_changed(self, widget):
        self.mergetree_check_ready()

    def mergetree_check_ready(self):
        ready = True
        if self.get_widget("mergetree_from_urls").get_active_text() == "":
            ready = False
        if self.get_widget("mergetree_to_urls").get_active_text() == "":
            ready = False

        self.assistant.set_page_complete(self.page, ready)
 
    #
    # Step 3: Merge Options
    #
    
    def on_mergeoptions_prepare(self):
        if self.last_page == 2:
            self.get_widget("mergeoptions_recursive").hide()
            self.get_widget("mergeoptions_ignore_ancestry").hide()
            self.get_widget("mergeoptions_only_record").hide()
        else:
            self.get_widget("mergeoptions_recursive").show()
            self.get_widget("mergeoptions_ignore_ancestry").show()
            self.get_widget("mergeoptions_only_record").show()
            
        self.assistant.set_page_complete(self.page, True)

class BranchMerge(InterfaceView):
    def __init__(self, path, branch1=None, branch2=None):
        InterfaceView.__init__(self, "branch-merge", "Merge")

        self.path = path
        self.branch1 = branch1
        self.branch2 = branch2
        self.vcs = rabbitvcs.vcs.VCS()

    def on_destroy(self, widget):
        self.destroy()
        
    def on_cancel_clicked(self, widget, data=None):
        self.close()

class GitMerge(BranchMerge):
    def __init__(self, path, branch1=None, branch2=None):
        BranchMerge.__init__(self, path, branch1, branch2)
        self.git = self.vcs.git(path)

        self.init_branch_widgets()

        self.from_branches = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("from_branch_container"),
            self.git,
            revision=self.branch1,
            url=path,
            expand=True,
            revision_changed_callback=self.__revision_changed
        )
        self.to_branches = rabbitvcs.ui.widget.RevisionSelector(
            self.get_widget("to_branch_container"),
            self.git,
            revision=self.branch2,
            url=path,
            expand=True,
            revision_changed_callback=self.__revision_changed
        )
        
        self.update_branch_info()

    def init_branch_widgets(self):

        self.info = {"from":{}, "to":{}}

        # FROM BRANCH INFO #
        from_container = self.get_widget("from_branch_info")
        to_container = self.get_widget("to_branch_info")
        
        # Set up the Author line
        author = gtk.Label(_("Author:"))
        author.set_size_request(90, -1)
        author.set_properties(xalign=0,yalign=0)
        self.info['from']['author'] = gtk.Label("")
        self.info['from']['author'].set_properties(xalign=0,yalign=0,selectable=True)
        self.info['from']['author'].set_line_wrap(True)
        author_container = gtk.HBox(False, 0)
        author_container.pack_start(author, False, False, 0)
        author_container.pack_start(self.info['from']['author'], False, False, 0)
        from_container.pack_start(author_container, False, False, 0)

        # Set up the Date line
        date = gtk.Label(_("Date:"))
        date.set_size_request(90, -1)
        date.set_properties(xalign=0,yalign=0)
        self.info['from']['date'] = gtk.Label("")
        self.info['from']['date'].set_properties(xalign=0,yalign=0,selectable=True)
        date_container = gtk.HBox(False, 0)
        date_container.pack_start(date, False, False, 0)
        date_container.pack_start(self.info['from']['date'], False, False, 0)
        from_container.pack_start(date_container, False, False, 0)

        # Set up the Revision line
        revision = gtk.Label(_("Revision:"))
        revision.set_size_request(90, -1)
        revision.set_properties(xalign=0,yalign=0)
        self.info['from']['revision'] = gtk.Label("")
        self.info['from']['revision'].set_properties(xalign=0,selectable=True)
        self.info['from']['revision'].set_line_wrap(True)
        revision_container = gtk.HBox(False, 0)
        revision_container.pack_start(revision, False, False, 0)
        revision_container.pack_start(self.info['from']['revision'], False, False, 0)
        from_container.pack_start(revision_container, False, False, 0)

        # Set up the Log Message line
        message = gtk.Label(_("Message:"))
        message.set_size_request(90, -1)
        message.set_properties(xalign=0,yalign=0)
        self.info['from']['message'] = gtk.Label("")
        self.info['from']['message'].set_properties(xalign=0,yalign=0,selectable=True)
        self.info['from']['message'].set_line_wrap(True)
        self.info['from']['message'].set_size_request(250, -1)
        message_container = gtk.HBox(False, 0)
        message_container.pack_start(message, False, False, 0)
        message_container.pack_start(self.info['from']['message'], False, False, 0)
        from_container.pack_start(message_container, False, False, 0)
        
        from_container.show_all()

        # Set up the Author line
        author = gtk.Label(_("Author:"))
        author.set_size_request(90, -1)
        author.set_properties(xalign=0,yalign=0)
        self.info['to']['author'] = gtk.Label("")
        self.info['to']['author'].set_properties(xalign=0,yalign=0,selectable=True)
        self.info['to']['author'].set_line_wrap(True)
        to_author_container = gtk.HBox(False, 0)
        to_author_container.pack_start(author, False, False, 0)
        to_author_container.pack_start(self.info['to']['author'], False, False, 0)
        to_container.pack_start(to_author_container, False, False, 0)

        # Set up the Date line
        date = gtk.Label(_("Date:"))
        date.set_size_request(90, -1)
        date.set_properties(xalign=0,yalign=0)
        self.info['to']['date'] = gtk.Label("")
        self.info['to']['date'].set_properties(xalign=0,yalign=0,selectable=True)
        to_date_container = gtk.HBox(False, 0)
        to_date_container.pack_start(date, False, False, 0)
        to_date_container.pack_start(self.info['to']['date'], False, False, 0)
        to_container.pack_start(to_date_container, False, False, 0)

        # Set up the Revision line
        revision = gtk.Label(_("Revision:"))
        revision.set_size_request(90, -1)
        revision.set_properties(xalign=0,yalign=0)
        self.info['to']['revision'] = gtk.Label("")
        self.info['to']['revision'].set_properties(xalign=0,selectable=True)
        self.info['to']['revision'].set_line_wrap(True)
        to_revision_container = gtk.HBox(False, 0)
        to_revision_container.pack_start(revision, False, False, 0)
        to_revision_container.pack_start(self.info['to']['revision'], False, False, 0)
        to_container.pack_start(to_revision_container, False, False, 0)

        # Set up the Log Message line
        message = gtk.Label(_("Message:"))
        message.set_size_request(90, -1)
        message.set_properties(xalign=0,yalign=0)
        self.info['to']['message'] = gtk.Label("")
        self.info['to']['message'].set_properties(xalign=0,yalign=0,selectable=True)
        self.info['to']['message'].set_line_wrap(True)
        self.info['to']['message'].set_size_request(250, -1)
        to_message_container = gtk.HBox(False, 0)
        to_message_container.pack_start(message, False, False, 0)
        to_message_container.pack_start(self.info['to']['message'], False, False, 0)
        to_container.pack_start(to_message_container, False, False, 0)
        
        to_container.show_all()

    def update_branch_info(self):
        from_branch = self.from_branches.get_revision_object()
        to_branch = self.to_branches.get_revision_object()

        if from_branch.value:
            log = self.git.log(self.path, limit=1, revision=from_branch, showtype="branch")
            if log:
                from_info = log[0]
                self.info['from']['author'].set_text(from_info.author)
                self.info['from']['date'].set_text(rabbitvcs.util.helper.format_datetime(from_info.date))
                self.info['from']['revision'].set_text(unicode(from_info.revision)[0:7])
                self.info['from']['message'].set_text(cgi.escape(rabbitvcs.util.helper.format_long_text(from_info.message, 500)))

        if to_branch.value:
            log = self.git.log(self.path, limit=1, revision=to_branch, showtype="branch")
            if log:
                to_info = log[0]
                self.info['to']['author'].set_text(to_info.author)
                self.info['to']['date'].set_text(rabbitvcs.util.helper.format_datetime(to_info.date))
                self.info['to']['revision'].set_text(unicode(to_info.revision)[0:7])
                self.info['to']['message'].set_text(cgi.escape(rabbitvcs.util.helper.format_long_text(to_info.message, 500)))

    def on_from_branches_changed(self, widget):
        self.update_branch_info()

    def on_to_branches_changed(self, widget):
        self.update_branch_info()

    def on_ok_clicked(self, widget, data=None):
        from_branch = self.from_branches.get_revision_object()
        to_branch = self.to_branches.get_revision_object()
        
        self.action = rabbitvcs.ui.action.GitAction(
            self.git,
            register_gtk_quit=self.gtk_quit_is_set()
        )
        
        self.action.append(
            self.git.merge,
            from_branch,
            to_branch
        )
        
        self.action.append(self.action.finish)
        self.action.start()

    def __revision_changed(self, widget):
        self.update_branch_info()

if __name__ == "__main__":
    from rabbitvcs.ui import main, VCS_OPT
    (options, args) = main(
        [VCS_OPT],
        usage="Usage: rabbitvcs merge path [revision... (for git)]"
    )

    path = args[0]

    vcs_name = options.vcs
    if not vcs_name:
        vcs_name = rabbitvcs.vcs.guess(path)["vcs"]    
    
    window = None
    if vcs_name == rabbitvcs.vcs.VCS_SVN:
        window = SVNMerge(path)
        window.register_gtk_quit()
        gtk.main()
    elif vcs_name == rabbitvcs.vcs.VCS_GIT:
        revision1 = None
        revision2 = None
        if len(args) == 2:
            revision1 = args[1]
        elif len(args) == 3:
            revision1 = args[1]
            revision2 = args[2]

        window = GitMerge(path, revision1, revision2)
        window.register_gtk_quit()
        gtk.main()
