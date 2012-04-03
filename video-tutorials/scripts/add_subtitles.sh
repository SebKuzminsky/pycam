#!/bin/sh

set -eu
test $# -ne 3 && echo >&2 "Three parameters are required: INPUT_VIDEO SUBTITLE_FILE OUTPUT_VIDEO" && exit 1

IN_FILE="$1"
SUBTITLE_FILE="$2"
OUT_FILE="$3"
ENCODING_OPTS="-ovc lavc -lavcopts vbitrate=1200"
SUBTITLE_OPTS="-utf8 -sub $SUBTITLE_FILE -subfont-text-scale 3 -subalign 0 -subpos 2"

mencoder $SUBTITLE_OPTS "$IN_FILE" -o "$OUT_FILE" $ENCODING_OPTS

