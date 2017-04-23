#!/usr/bin/env sh
cd $(dirname "$0")/..

mkdir build
mkdir build/images
rm build/images/*.png

#./runner.py --arm_tools_dir=/Users/behrens/pebble-dev/arm-cs-tools examples/pebble &
#sleep 0.5s

#PAGERES=(pageres 750x500 --selector='#inner_content')
PAGERES=(pageres 750x500)

URL_FILE=http://127.0.0.1:5000/path/Users/behrens/.platformio/packages/framework-arduinoteensy/cores/teensy3/usb_dev.c/?sort=code_desc
URL_FOLDER=http://127.0.0.1:5000/path/lib/KBox/src/?sort=code_desc
URL_FUNCTION=http://127.0.0.1:5000/path/lib/KBox/src/pages/BatteryMonitorPage.cpp/_ZN18BatteryMonitorPage17formatMeasurementEfPKc/
${PAGERES[@]} --filename='build/images/folder' $URL_FOLDER
${PAGERES[@]} --filename='build/images/file' $URL_FILE
${PAGERES[@]} --filename='build/images/function' $URL_FUNCTION

convert build/images/function.png build/images/file.png build/images/folder.png +append images/overview.png

#kill $(jobs -p)
