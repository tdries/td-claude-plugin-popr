#!/bin/bash
# Double click me. Right click → Open the first time: POPR is not code signed,
# so a plain double click hits a Gatekeeper warning with no way past.
cd "$(dirname "$0")/.." || exit 1
./install.sh
echo
echo "Press return to close."
read -r _
