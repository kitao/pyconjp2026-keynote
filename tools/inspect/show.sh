#!/bin/sh
# Open only what has already been checked:  ./show.sh 4
open "$(dirname "$0")/../render/P$1.png"
