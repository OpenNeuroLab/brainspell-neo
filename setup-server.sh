#!/bin/bash

# A script to configure Brainspell to launch on startup, along with installing and configuring Supervisor.

pip2 install supervisor

python3 server/generate_supervisor.py `which python3` `pwd` > server/supervisord.conf