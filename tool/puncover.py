#!/usr/bin/env python

import argparse
from distutils.spawn import find_executable
import os
from flask import Flask
from os.path import dirname
from collector import Collector
import renderers

def build_collector(arm_tools_dir, project_dir=None, elf_file=None, su_dir=None):
    c = Collector(arm_tools_dir=arm_tools_dir)
    if project_dir:
        # project_dir = os.path.abspath(project_dir)
        # TODO: check if this is a pebble project dir
        c.parse_pebble_project_dir(project_dir)
    if elf_file:
        c.parse(elf_file, su_dir)

    c.enhance()
    return c


app = Flask(__name__)


def find_arm_tools_location():
    obj_dump = find_executable("arm-none-eabi-objdump")
    return dirname(dirname(obj_dump)) if obj_dump else None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pebble build analyzer")

    parser.add_argument('--arm_tools_dir', dest='arm_tools_dir', default=find_arm_tools_location(),
                        help='location of your arm tools. Typically ~/pebble-dev/PebbleSDK-current/arm-cs-tools')
    parser.add_argument('--elf_file', dest="elf_file",
                        help='location of an ELF file')
    parser.add_argument('project_dir', metavar='project_dir', nargs='?',
                        help='location of your pebble project')
    args = parser.parse_args()

    if not args.project_dir and not args.elf_file:
        raise Exception("Specify either a project directory or an ELF file.")

    collector = build_collector(project_dir=args.project_dir, elf_file=args.elf_file, arm_tools_dir=args.arm_tools_dir)

    renderers.register_jinja_filters(app.jinja_env)
    renderers.register_urls(app, collector)

    app.run(debug=True)
