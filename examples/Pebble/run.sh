#!/usr/bin/env sh
set -e
cd $(dirname "$0")

echo "-------------------------"
echo "Pebble Compass"
if [ ! -d "pebble-compass" ]; then
    git clone git@github.com:HBehrens/pebble-compass.git
fi
cd pebble-compass
# version as it was at the time of writing this
# it's known to work
git reset --hard 11062cb0ec069723d383e3e0a14ca92e93ccd5eb

echo "-------------------------"
echo "PebbleSDK"

# TODO

if ! command -v pebble 2>/dev/null; then
    echo "Make sure Pebble SDK is installed and 'pebble' command is on path."
    echo "https://developer.pebble.com/sdk/install/"
    exit 1
fi

pebble build

echo "-------------------------"
echo "puncover"

gcc_tools_path=~/pebble-dev/arm-cs-tools/bin/arm-none-eabi-
if [ ! -f ${gcc_tools_path}objdump ]; then
    echo "Make sure ${gcc_tools_path}objdump exists"
    exit 1
fi

puncover --gcc_tools_base ${gcc_tools_path} \
         --elf build/basalt/pebble-app.elf \
         --build_dir build \
         --src_root . \
         &
puncover_pid=$!
trap "kill $puncover_pid" EXIT

if [ "$1" = "--wget" ]; then
    sleep 5 # dirty way to give puncover enough time to launch webserver
    echo "-------------------------"
    echo "wget"
    rm -rf wget
    mkdir wget
    cd wget
    wget -e robots=off -r -l 2 localhost:5000
else
    # infinite wait, user has to hit CTRL+C to exit
    # puncover, executed as background job will be killed through trap
    wait
fi
