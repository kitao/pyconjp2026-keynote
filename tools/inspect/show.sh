#!/bin/sh
# 確認が済んだものだけを開く： ./show.sh 4
open "$(dirname "$0")/../render/P$1.png"
