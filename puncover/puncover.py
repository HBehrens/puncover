#!/usr/bin/env python

import argparse
import os
import webbrowser
from distutils.spawn import find_executable
from os.path import dirname
from threading import Timer

from flask import Flask

from puncover import renderers
from puncover.builders import ElfBuilder
from puncover.collector import Collector
from puncover.gcc_tools import GCCTools
from puncover.middleware import BuilderMiddleware
from puncover.version import __version__


def create_builder(gcc_base_filename, elf_file=None, su_dir=None, src_root=None):
    c = Collector(GCCTools(gcc_base_filename))
    if elf_file:
        return ElfBuilder(c, src_root, elf_file, su_dir)
    else:
        raise Exception("Unable to configure builder for collector")


app = Flask(__name__)


def find_arm_tools_location():
    obj_dump = find_executable("arm-none-eabi-objdump")
    return dirname(dirname(obj_dump)) if obj_dump else None


def open_browser(host, port):
    webbrowser.open_new("http://{}:{}/".format(host, port))


def main():
    parser = argparse.ArgumentParser(
        description="Analyses C/C++ build output for code size, static variables, and stack usage."
    )
    parser.add_argument(
        "--arm_tools_dir",
        dest="arm_tools_dir",
        default=find_arm_tools_location(),
        help="DEPRECATED! location of your arm tools.",
    )
    parser.add_argument(
        "--gcc_tools_base",
        dest="gcc_tools_base",
        help="filename prefix for your gcc tools, e.g. ~/arm-cs-tools/bin/arm-none-eabi-",
    )
    parser.add_argument(
        "--elf_file", dest="elf_file", required=True, help="location of an ELF file"
    )
    parser.add_argument("--src_root", dest="src_root", help="location of your sources")
    parser.add_argument(
        "--build_dir", dest="build_dir", help="location of your build output"
    )
    parser.add_argument("--debug", action="store_true", help="enable Flask debugger")
    parser.add_argument(
        "--port",
        dest="port",
        default=5000,
        type=int,
        help="port the HTTP server runs on",
    )
    parser.add_argument(
        "--host",
        dest="host",
        default="127.0.0.1",
        help="host IP the HTTP server runs on",
    )
    parser.add_argument(
        "--no-open-browser",
        action="store_true",
        help="don't automatically open a browser window",
    )
    args = parser.parse_args()

    if not args.gcc_tools_base:
        if args.arm_tools_dir:
            print(
                "DEPRECATED: argument --arm_tools_dir will be removed, use --gcc_tools_base instead."
            )
            args.gcc_tools_base = os.path.join(args.arm_tools_dir, "bin/arm-none-eabi-")

    builder = create_builder(
        args.gcc_tools_base,
        elf_file=args.elf_file,
        src_root=args.src_root,
        su_dir=args.build_dir,
    )
    builder.build_if_needed()
    renderers.register_jinja_filters(app.jinja_env)
    renderers.register_urls(app, builder.collector)
    app.wsgi_app = BuilderMiddleware(app.wsgi_app, builder)

    if args.debug:
        app.debug = True

    # Open a browser window, only if this is the first instance of the server
    # from https://stackoverflow.com/a/63216793
    if not args.no_open_browser and not os.environ.get("WERKZEUG_RUN_MAIN"):
        # wait one second before starting, so the flask server is ready and we
        # don't see a 404 for a moment first
        Timer(1, open_browser, kwargs={"host": args.host, "port": args.port}).start()

    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
