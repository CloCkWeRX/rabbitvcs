#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
# Copyright (C) 2009 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2009 by Adam Plumb <adamplumb@gmail.com>#
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

import os
import threading
from Queue import Queue

#    ATTENTION: Developers and hackers!
# The following lines allow you to select between different status checker
# implementations. Simply uncomment one to try it out - there's nothing else you
# have to do.

# from rabbitvcs.services.checkerservice import StatusCheckerStub as StatusChecker
# from rabbitvcs.services.simplechecker import StatusChecker
# from rabbitvcs.services.statuschecker import StatusChecker
from rabbitvcs.services.checkers.loopedchecker import StatusChecker

import rabbitvcs.vcs.svn
import rabbitvcs.vcs.status
import rabbitvcs.util.helper

from rabbitvcs import gettext
_ = gettext.gettext

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.services.statuscheckerplus")

class StatusCheckerPlus:

    CHECKER_NAME = _("Multi-process status checker")

    #: The queue will be populated with 4-ples of
    #: (path, recurse, invalidate, callback).
    _paths_to_check = Queue()

    def __init__(self):
        """ Creates a new status cache.

        This will start the necessary worker thread and subprocess for checking.
        """
        self.worker = threading.Thread(target = self._status_update_loop,
                                       name = "Status cache thread")

        self.client = rabbitvcs.vcs.create_vcs_instance()

        self._alive = threading.Event()
        self._alive.set()

        # We need a checker for each thread (if we use locks, we're right back
        # where we started from).
        self.checker = StatusChecker()
        self.other_checker = StatusChecker()
        # self.worker.setDaemon(True)
        self.worker.start()

    def check_status(self, path,
                       recurse=False, invalidate=False,
                       summary=False, callback=None):
        # The invalidate parameter is not used.
        status = None
                
        if callback:
            status = \
            self._check_status_with_callback(path, recurse, summary, callback)
        else:
            status = \
            self._check_status_without_callback(path, self.checker, recurse,
                                                summary)

        return status
    
    def _check_status_with_callback(self, path, recurse=False,
                                         summary=False, callback=None):

        if self.client.is_in_a_or_a_working_copy(path):
            single = rabbitvcs.vcs.status.Status.status_calc(path)
            self._paths_to_check.put((path, recurse, summary, callback))
        else:
            single = rabbitvcs.vcs.status.Status.status_unknown(path)

        if summary:
            single.make_summary()
            
        return single
        
    def _check_status_without_callback(self, path, checker, recurse=False,
                                            summary=False):

        # Uncomment this for useful simulation of a looooong status check :)
        # log.debug("Sleeping for 10s...")
        # time.sleep(5)
        # log.debug("Done.")

        
        path_status = \
            checker.check_status(path, recurse, summary)
               
        return path_status
        
    def extra_info(self):
        pid1 = self.checker.get_extra_PID()
        pid2 = self.other_checker.get_extra_PID()
        mypid = os.getpid()
        return [
                (_("DBUS service memory usage"),
                    "%s KB" % rabbitvcs.util.helper.process_memory(mypid)),
                (_("Synchronous checker memory usage"),
                    "%s KB" % rabbitvcs.util.helper.process_memory(pid1)),
                (_("Asynchronous checker memory usage"),
                    "%s KB" % rabbitvcs.util.helper.process_memory(pid2)),
                (_("Synchronous checker PID"), str(pid1)),
                (_("Asynchronous checker PID"), str(pid2)),
                ]

    def get_memory_usage(self):
        """ Returns any additional memory of any subprocesses used by this
        checker. In other words, DO NOT return the memory usage of THIS process!
        """
        return (self.checker.get_memory_usage()
                + self.other_checker.get_memory_usage())


    def quit(self):
        """ Stops operation of the checker. Future calls to check_status will
        just get old information or a "calculating status", and callbacks will
        never be called.

        This is here so that we can do necessary cleanup. There might be a GUI
        interface to kill the enclosing service at some later date.
        """
        self._alive.clear()
        self._paths_to_check.put(None)
        self.worker.join()
        self.checker.quit()
        self.other_checker.quit()

    def _status_update_loop(self):
        """ This loops until the status cache is "killed" (via the quit()
        method), checking for new paths and doing the status check accordingly.
        """
        # This loop will stop when the thread is killed via the quit() method
        while self._alive.isSet():
            next = self._paths_to_check.get()

            # This is a bit hackish, but basically when the quit method is
            # called, if we're idle we'll never know. This is a way of
            # interrupting the Queue.
            if next:
                (path, recurse, summary, callback) = next
            else:
                continue

            self._update_path_status(path, recurse, summary, callback)

        log.debug("Exiting status cache update loop")

    def _update_path_status(self, path, recurse=False,
                               summary=False, callback=None):
                
        status = self._check_status_without_callback(path, self.other_checker,
                                                     recurse, summary)

        callback(status)
