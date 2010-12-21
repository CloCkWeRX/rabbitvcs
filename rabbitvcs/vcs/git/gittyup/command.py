#
# command.py
#

import subprocess
import fcntl
import select
import os

from exceptions import GittyupCommandError

def notify_func(data):
    pass

def cancel_func():
    return False

class GittyupCommand:
    def __init__(self, command, cwd=None, notify=None, cancel=None):
        self.command = command
        
        self.notify = notify_func
        if notify:
            self.notify = notify

        self.get_cancel = cancel_func
        if cancel:
            self.get_cancel = cancel

        self.cwd = cwd
        if not self.cwd:
            self.cwd = os.getcwd()
    
    def get_lines(self, val):
        returner = []
        lines = val.rstrip("\n").split("\n")
        for line in lines:
            returner.append(line.rstrip("\x1b[K\n"))
        
        return returner 

    def execute(self):
        proc = subprocess.Popen(self.command, 
                                cwd=self.cwd,
                                stdin=None,
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE,
                                close_fds=True)
        
        fcntl.fcntl(
            proc.stdout.fileno(),
            fcntl.F_SETFL,
            fcntl.fcntl(proc.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK,
        )

        stdout = []
        last_chunk = ""
        while True:
            readx = select.select([proc.stdout.fileno()], [], [])[0]
            if readx:
                chunk = last_chunk + proc.stdout.read()
                if chunk == '':
                    break
                    
                if chunk[-1] != "\n":
                    last_chunk = chunk
                    continue
                
                lines = self.get_lines(chunk)
                
                for line in lines:
                    self.notify(line)
                    stdout.append(line)
                
                chunk = ""
                last_chunk = ""

            if self.get_cancel():
                proc.kill()

        if chunk:
            lines = self.get_lines(chunk)
            
            for line in lines:
                self.notify(line)
                stdout.append(line)

        return (0, stdout, None)
