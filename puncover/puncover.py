#!/usr/bin/env python

import argparse
import importlib.metadata
import os
import webbrowser
from os.path import dirname
from shutil import which
from threading import Timer

from flask import Flask

from puncover import renderers
from puncover.builders import ElfBuilder
from puncover.collector import Collector
from puncover.gcc_tools import GCCTools
from puncover.middleware import BuilderMiddleware

version = importlib.metadata.version("puncover")

# Default listening port. Fallback to 8000 if the default port is already in use.
DEFAULT_PORT = 5000
DEFAULT_PORT_FALLBACK = 8000


def is_port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def get_default_port():
    return DEFAULT_PORT if not is_port_in_use(DEFAULT_PORT) else DEFAULT_PORT_FALLBACK


def create_builder(gcc_base_filename, elf_file=None, su_dir=None, src_root=None):
    c = Collector(GCCTools(gcc_base_filename))
    if elf_file:
        return ElfBuilder(c, src_root, elf_file, su_dir)
    else:
        raise Exception("Unable to configure builder for collector")


app = Flask(__name__)


def get_arm_tools_prefix_path():
    """
    Try to find and return the arm tools triple prefix path, like this:
      /usr/local/gcc-arm-none-eabi-9-2019-q4-major/bin/arm-none-eabi-

    It's used to invoke the other tools, like objdump/nm.

    Note that we could instead use the '-print-prog-name=...' option to gcc,
    which returns the paths we need. For now stick with the hacky method here.
    """
    obj_dump = which("arm-none-eabi-objdump")
    if not obj_dump:
        return None

    gcc_tools_base_dir = dirname(dirname(obj_dump))
    assert gcc_tools_base_dir, "Unable to find gcc tools base dir from {}".format(obj_dump)

    return os.path.join(gcc_tools_base_dir, "bin/arm-none-eabi-")


def open_browser(host, port):
    webbrowser.open("http://{}:{}/".format(host, port))

def main():
    gcc_tools_base = get_arm_tools_prefix_path()

    parser = argparse.ArgumentParser(
        description="Analyses C/C++ build output for code size, static variables, and stack usage.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--gcc-tools-base",
        "--gcc_tools_base",
        default=gcc_tools_base,
        help="filename prefix for your gcc tools, e.g. ~/arm-cs-tools/bin/arm-none-eabi-",
    )
    parser.add_argument(
        "elf_file", nargs="?", help="location of an ELF file (positional or --elf_file)"
    )
    parser.add_argument(
        "--elf",
        "--elf_file",
        dest="elf_file_opt",
        help="location of an ELF file (positional or --elf_file)",
    )
    parser.add_argument("--src_root", "--src-root", help="location of your sources")
    parser.add_argument("--build_dir", "--build-dir", help="location of your build output")
    parser.add_argument("--debug", action="store_true", help="enable Flask debugger")
    parser.add_argument(
        "--port",
        dest="port",
        default=get_default_port(),
        type=int,
        help="port the HTTP server runs on",
    )
    parser.add_argument("--host", default="127.0.0.1", help="host IP the HTTP server runs on")
    parser.add_argument(
        "--no-open-browser", action="store_true", help="don't automatically open a browser window"
    )
    parser.add_argument(
        '--no-interactive',
        '--no_interactive',
        action='store_true',
        help="don't start the interactive website to browse the elf analysis"
    )
    parser.add_argument('--generate-report', '--generate_report', action='store_true')
    parser.add_argument('--report-type', '--report_type', default="json")
    parser.add_argument('--report-filename', '--report_filename', default="report")
    parser.add_argument(
        '--report-max-static-stack-usage',
        '--report_max_static_stack_usage',
        action='append',
        help="display_name[:max_stack_size] of functions to report the worst case static stack size with i.e. bg_thread_main or bg_thread_main:1024"
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + version)
    args = parser.parse_args()

    # Determine ELF file from positional or optional argument
    elf_file = args.elf_file_opt if args.elf_file_opt else args.elf_file
    if not elf_file:
        parser.error("the following arguments are required: elf_file (positional or --elf_file)")

    if args.gcc_tools_base is None:
        print(
            "Unable to find gcc tools base dir (tried searching for 'arm-none-eabi-objdump' on PATH), please specify --gcc-tools-base"
        )
        exit(1)

    builder = create_builder(
        args.gcc_tools_base, elf_file=elf_file, src_root=args.src_root, su_dir=args.build_dir
    )
    builder.build_if_needed()
    if args.generate_report:
        builder.collector.report_max_static_stack_usages_from_function_names(args.report_max_static_stack_usage,
                                                           filename=args.report_filename, report_type=args.report_type)

    renderers.register_jinja_filters(app.jinja_env)
    renderers.register_urls(app, builder.collector)
    app.wsgi_app = BuilderMiddleware(app.wsgi_app, builder)

    if args.debug:
        app.debug = True

    if not args.no_interactive:
        if is_port_in_use(args.port):
            print("Port {} is already in use, please choose a different port.".format(args.port))
            exit(1)

        # Open a browser window, only if this is the first instance of the server
        # from https://stackoverflow.com/a/63216793
        if not args.no_open_browser and not os.environ.get("WERKZEUG_RUN_MAIN"):
            # wait one second before starting, so the flask server is ready and we
            # don't see a 404 for a moment first
            Timer(1, open_browser, kwargs={"host":args.host, "port":args.port}).start()

        app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
