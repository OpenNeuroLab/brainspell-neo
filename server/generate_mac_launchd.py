launchd_script = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.brainspell.supervisord</string>
    <key>ProgramArguments</key>
    <array>
        <string>{0}</string>
        <string>-c</string>
        <string>{1}/server/supervisord.conf</string>
    </array>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>"""

import sys

assert len(sys.argv) == 3, "Wrong number of arguments. Expected supervisord location as the first argument, and brainspell location as the second."

supervisor_location = sys.argv[1]
brainspell_location = sys.argv[2]

print(launchd_script.format(supervisor_location, brainspell_location))