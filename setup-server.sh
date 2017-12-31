#!/bin/bash

# A script to configure Brainspell to launch on startup, along with installing and configuring Supervisor.

pip2 install supervisor

current_directory=${PWD##*/}

if [ $current_directory = "brainspell-neo" ]
then
    python3 server/generate_supervisor.py `which python3` `pwd` > server/supervisord.conf
else
    echo "Not in the brainspell-neo directory. Please run again when you're in the correct directory."
fi