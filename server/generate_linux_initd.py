initd_script = """#!/bin/sh
### BEGIN INIT INFO
# Provides:
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start supervisord daemon at boot time
# Description:       Start supervisord for use with Brainspell.
### END INIT INFO

dir="{1}/server/supervisord.conf"
cmd="{0}"
"""
initd_script_ending = """
name='brainspell_supervisord'

case "$1" in
    start)
    echo "Starting $name"
    echo "$cmd -c $dir &"
    $cmd -c $dir &
    ;;
    stop)
    echo "Stopping $name..."
    kill `cat /tmp/supervisord.pid`
    for i in 1 2 3 4 5
    do
        echo "."
        sleep 1
    done
    echo

    echo "Stopped"
    ;;
    restart)
    $0 stop
    $0 start
    ;;
    status)
    echo "Cannot determine status."
    ;;
    *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac

exit 0"""

import sys

assert len(sys.argv) == 3, "Wrong number of arguments. Expected supervisord location as the first argument, and brainspell location as the second."

supervisor_location = sys.argv[1]
brainspell_location = sys.argv[2]

print(initd_script.format(supervisor_location, brainspell_location) + initd_script_ending)