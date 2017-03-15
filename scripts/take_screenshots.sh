#!/usr/bin/env sh
cd $(dirname "$0")/..

mkdir build
mkdir build/images
rm build/images/*.png

./runner.py --arm_tools_dir=/Users/behrens/pebble-dev/arm-cs-tools examples/pebble &
sleep 0.5s

PAGERES="pageres 750x500"
BASE_URL="http://127.0.0.1:5000/path/Users/behrens/Documents/projects/pebble/puncover/pebble"
$PAGERES --filename='build/images/function' $BASE_URL/src/side_effect.c/use_ptr/
$PAGERES --filename='build/images/file' $BASE_URL/src/side_effect.c/
$PAGERES --filename='build/images/folder' $BASE_URL/src/

convert build/images/function.png build/images/file.png build/images/folder.png +append images/overview.png

kill $(jobs -p)
