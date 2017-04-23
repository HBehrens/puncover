#!/usr/bin/env sh
set -e
cd $(dirname "$0")

echo "-------------------------"
echo "KBox firmware"
if [ ! -d "kbox-firmware" ]; then
    git clone https://github.com/sarfata/kbox-firmware.git
fi
cd kbox-firmware
# version as it was at the time of writing this
# it's known to work
git reset --hard 9216416c9f4fc436bc061273042e0dcf6a54c560

echo "-------------------------"
echo "PlatformIO"
pip install -U platformio
platformio run -e host

echo "-------------------------"
echo "puncover"
puncover --gcc_tools_base ~/.platformio/packages/toolchain-gccarmnoneeabi/bin/arm-none-eabi- \
         --elf .pioenvs/host/firmware.elf \
         --build_dir .pioenvs/host \
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
