#!/usr/bin/env python

import argparse
import os
from distutils.spawn import find_executable
from flask import Flask
from os.path import dirname
from collector import Collector
from builders import PebbleProjectBuilder, ElfBuilder
from middleware import BuilderMiddleware
import renderers
from gcc_tools import GCCTools


def create_builder(gcc_base_filename, project_dir=None, elf_file=None, su_dir=None, src_root=None):
    c = Collector(GCCTools(gcc_base_filename))
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


def main():
    parser = argparse.ArgumentParser(description="Pebble build analyzer")
    parser.add_argument('--arm_tools_dir', dest='arm_tools_dir', default=find_arm_tools_location(),
                        help='DEPRECATED! location of your arm tools. Typically ~/pebble-dev/PebbleSDK-current/arm-cs-tools')
    parser.add_argument('--gcc_tools_base', dest='gcc_tools_base',
                        help='filename prefix for your gcc tools, e.g. ~/arm-cs-tools/bin/arm-none-eabi-')
    parser.add_argument('--elf_file', dest="elf_file",
                        help='location of an ELF file')
    parser.add_argument('--src_root', dest='src_root',
                        help='location of your sources')
    parser.add_argument('--build_dir', dest='build_dir',
                        help='location of your build output')
    parser.add_argument('--debug', action='store_true',
                        help='enable Flask debugger')
    parser.add_argument('--port', dest='port', default=5000, type=int,
                        help='port the HTTP server runs on')
    parser.add_argument('project_dir', metavar='project_dir', nargs='?',
                        help='location of your pebble project')
    args = parser.parse_args()
    if not args.project_dir and not args.elf_file:
        raise Exception("Specify either a project directory or an ELF file.")

    if not args.gcc_tools_base:
        if args.arm_tools_dir:
            print('DEPRECATED: argument --arm_tools_dir will be removed, use --gcc_tools_base instead.')
            args.gcc_tools_base = os.path.join(args.arm_tools_dir, 'bin/arm-none-eabi-')

    builder = create_builder(args.gcc_tools_base, project_dir=args.project_dir, elf_file=args.elf_file,
                             src_root=args.src_root, su_dir=args.build_dir)
    builder.build_if_needed()
    renderers.register_jinja_filters(app.jinja_env)
    renderers.register_urls(app, builder.collector)
    app.wsgi_app = BuilderMiddleware(app.wsgi_app, builder)

    if args.debug:
        app.debug = True
    app.run(port=args.port)


if __name__ == '__main__':
    main()
