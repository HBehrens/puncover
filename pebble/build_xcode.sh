#!/bin/sh

PEBBLE_SDK=~/pebble-dev/PebbleSDK-current
/usr/bin/pebblex build --pebble_sdk=$PEBBLE_SDK
../tool/puncover.py json .gutter.json --pebble_sdk=$PEBBLE_SDK
../tool/puncover.py html build/puncover --pebble_sdk=$PEBBLE_SDK