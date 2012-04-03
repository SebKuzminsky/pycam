#!/bin/sh
#
# merge a subtitles file with a video
# Syntax: ./merge_and_fix.sh LANG

set -eu

# "noskip" is necessary due to some weird frames in the original video
lang=$1

mencoder -subfont-text-scale 3 -subalign 0 -subpos 0 -utf8 -sub multi-layer-2D.${lang}.srt multi-layer-2D.ogv -o multi-layer-2D.${lang}.mpg4 -noskip -forceidx -ovc lavc -lavcopts vbitrate=1200

