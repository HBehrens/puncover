#!/usr/bin/env python

import argparse
from distutils.spawn import find_executable
from flask import Flask
from os.path import dirname
from collector import Collector
from builders import PebbleProjectBuilder, ElfBuilder
from middleware import BuilderMiddleware
import renderers


def create_builder(arm_tools_dir, project_dir=None, elf_file=None, su_dir=None, src_root=None):
    c = Collector(arm_tools_dir=arm_tools_dir)
    if project_dir:
        return PebbleProjectBuilder(c, src_root, project_dir)
    elif elf_file:
        return ElfBuilder(c, src_root, elf_file, su_dir)
    else:
        raise Exception("Unable to configure builder for collector")

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
    parser.add_argument('--src_root', dest='src_root',
                        help='location of your sources')
    parser.add_argument('--build_dir', dest='build_dir',
                        help='location of your build output')
    parser.add_argument('--port', dest='port', default=5000, type=int,
                        help='port the HTTP server runs on')
    parser.add_argument('project_dir', metavar='project_dir', nargs='?',
                        help='location of your pebble project')
    args = parser.parse_args()

    if not args.project_dir and not args.elf_file:
        raise Exception("Specify either a project directory or an ELF file.")

    builder = create_builder(project_dir=args.project_dir, elf_file=args.elf_file, arm_tools_dir=args.arm_tools_dir,
                                src_root=args.src_root, su_dir=args.build_dir)

    builder.build_if_needed()

    renderers.register_jinja_filters(app.jinja_env)
    renderers.register_urls(app, builder.collector)

    app.wsgi_app = BuilderMiddleware(app.wsgi_app, builder)
    app.run(debug=True, port=args.port)
