#!/bin/sh

ORIG_FILE="cropped.avi"
#MENCODER_OPTS="-ovc raw -noskip -forceidx -vf harddup -vf crop=1024:640:232:260"
MENCODER_OPTS="-ovc raw -noskip -forceidx -vf harddup"
TIME1="-ss 1:07 -endpos 58 $ORIG_FILE -o cropped1.avi"
TIME2="-ss 4:13 -endpos 75 $ORIG_FILE -o cropped2.avi"
TIME3="-ss 6:10 -endpos 7 $ORIG_FILE -o cropped3.avi"


mencoder $MENCODER_OPTS $TIME1
mencoder $MENCODER_OPTS $TIME2
mencoder $MENCODER_OPTS $TIME3
mencoder -idx -ovc raw cropped1.avi cropped2.avi cropped3.avi -o cropped_all.avi

