"""
A deployment script that accomplishes the following:

Sets up a handler for the endpoint /deploy, which when triggered on a production port:

1) Navigates into a "debug" directory, where it pulls the latest copy of Brainspell from GitHub (or clones a copy, if one doesn't already exist)
2) Starts the "debug" Brainspell server at port 5858.
3) Triggers the /deploy endpoint on the debug server locally, which:
    a) Navigates out of the "debug" directory, and pulls a fresh copy of the GitHub repo for the production server.

This process ensures that a GitHub push is only deployed to production if:
i) The server can successfully run and
ii) The deploy endpoint on the server still exists.
"""

import subprocess
import argparse
import os
from user_accounts import BaseHandler
import tornado.ioloop
from time import sleep


def subprocess_cmd_sync(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    proc_stdout = process.communicate()[0].strip()


def subprocess_cmd_async(command):
    subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)


class DeployHandler(BaseHandler):
    def get(self):
        # get the port that is currently running
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-p',
            metavar="--port",
            type=int,
            help='a port to run the server on',
            default=5000)
        args = parser.parse_args()
        if args.p == 5000:
            port_to_run = int(os.environ.get("PORT", args.p))
        else:
            port_to_run = args.p

        if port_to_run == 5858:
            # if the server is running on a debug port
            print(
                "Debug server: Navigating into the parent directory, and pulling from the git repo.")
            subprocess_cmd_sync(
                "cd ../../; git pull origin master; python3 json_api/brainspell.py")
            print("Debug server: Finished. Closing debug server.")
            tornado.ioloop.IOLoop.instance().stop()
        else:
            # if this is a production port
            """
            Note that all shell commands executed are idempotent. If a folder already exists, for example, mkdir does nothing.
            """
            print("Production server: Cloning the Brainspell git repo into a debug folder, if one doesn't already exist, then pulling...")
            init_commands = "mkdir debug &>/dev/null; cd debug; git clone https://github.com/OpenNeuroLab/brainspell-neo.git &>/dev/null; git pull origin master"
            # clone/pull the debug server
            subprocess_cmd_sync(init_commands)

            print("Production server: Starting debug server...")
            subprocess_cmd_async(
                "cd debug/brainspell-neo; python3 json_api/brainspell.py -p 5858 &")
            sleep(.5)
            print("Production server: Pinging /deploy endpoint of debug server...")
            subprocess_cmd_async("wget -qO- localhost:5858/deploy &>/dev/null")
            print("Production server: Done.")
