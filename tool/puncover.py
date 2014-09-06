from __future__ import print_function
import fnmatch
import json
import os
from pprint import pprint
import re
import shutil
import subprocess
import sys
import jinja2

NAME = "name"
SIZE = "size"
FILE = "file"
BASE_FILE = "base_file"
LINE = "line"
ASM = "asm"
STACK_SIZE = "stack_size"
STACK_QUALIFIERS = "stack_qualifiers"
ADDRESS = "address"
TYPE = "type"
TYPE_FUNCTION = "function"

def warning(*objs):
    print("WARNING: ", *objs, file=sys.stderr)

class Collector:

    def __init__(self):
        self.symbols = {}

    def qualified_symbol_name(self, symbol):
        return "%s/%s" % (symbol[BASE_FILE], symbol[NAME]) if symbol.has_key(BASE_FILE) else symbol[NAME]

    def symbol(self, name):
        for s in self.symbols.values():
            if self.qualified_symbol_name(s) == name:
                return s
        return None

    def add_symbol(self, name, address, size=None, file=None, line=None, assembly_lines=None):
        sym = self.symbols.get(address, {})
        if sym.has_key(NAME) and sym[NAME] != name:
            warning("Name for symbol at %s inconsistent (was '%s', now '%s')" % (address, sym[NAME], name))
        else:
            sym[NAME] = name
        if size:
            sym[SIZE] = int(size)
        if file:
            sym[FILE] = file
            sym[BASE_FILE] = os.path.basename(file)
        if line:
            sym[LINE] = line
        if assembly_lines:
            sym[ASM] = assembly_lines
            sym[TYPE] = TYPE_FUNCTION
        sym[ADDRESS] = address

        self.symbols[address] = sym

    def parse_size_line(self, line):
        # 00000550 00000034 T main	/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c:25
        pattern = re.compile(r"^([\da-f]{8})\s+([\da-f]{8})\s+(.)\s+(\w+)(\s+([^:]+):(\d+))?")
        match = pattern.match(line)
        if not match:
            return False

        addr = match.group(1)
        size = int(match.group(2), 16)
        type = match.group(3)
        name = match.group(4)
        if match.group(5):
            file = match.group(6)
            line = int(match.group(7))
        else:
            file = None
            line = None

        self.add_symbol(name, address=addr, size=size, file=file, line=line)

        return True

    def parse_assembly_text(self, assembly):
        name = None
        addr = None
        assembly_lines = []
        found_symbols = 0

        def flush_current_symbol():
            if name and addr:
                self.add_symbol(name, addr, assembly_lines=assembly_lines)
                return 1
            return 0

        # 00000098 <pbl_table_addr>:
        function_start_pattern = re.compile(r"^([\da-f]{8})\s+<(\w+)>:")
        for line in assembly.split("\n"):
            match = function_start_pattern.match(line)
            if match:
                found_symbols += flush_current_symbol()
                addr = match.group(1)
                name = match.group(2)
                assembly_lines = []
            else:
                assembly_lines.append(line)

        found_symbols += flush_current_symbol()
        return found_symbols

    def parse_stack_usage_line(self, line):
        # puncover.c:8:43:dynamic_stack2	16	dynamic
        # puncover.c:14:40:0	16	dynamic,bounded
        # puncover.c:8:43:dynamic_stack2	16	dynamic
        pattern = re.compile(r"^(.*?\.c):(\d+):(\d+):([^\s]+)\s+(\d+)\s+([a-z,]+)")
        match = pattern.match(line)
        if not match:
            return False

        base_file_name = match.group(1)
        line = int(match.group(2))
        symbol_name = match.group(4)
        stack_size = int(match.group(5))
        stack_qualifier = match.group(6)

        return self.add_stack_usage(base_file_name, line, symbol_name, stack_size, stack_qualifier)

    def add_stack_usage(self, base_file_name, line, symbol_name, stack_size, stack_qualifier):
        for addr, symbol in self.symbols.items():
            if symbol.get(BASE_FILE, None) == base_file_name and symbol.get(LINE, None) == line:
                    symbol[STACK_SIZE] = stack_size
                    symbol[STACK_QUALIFIERS] = stack_qualifier
                    return True

        warning("Couldn't find symbol for %s:%d:%s" % (base_file_name, line, symbol_name))
        return False

    def parse_pebble_build_dir(self, dir):
        def get_assembly_lines(dir):
            proc = subprocess.Popen(['arm-none-eabi-objdump','-dslw', 'pebble-app.elf'], stdout=subprocess.PIPE, cwd=dir)
            return proc.stdout.readlines()


        def get_size_lines(dir):
            proc = subprocess.Popen(['arm-none-eabi-nm','-Sl', 'pebble-app.elf'], stdout=subprocess.PIPE, cwd=dir)
            return proc.stdout.readlines()


        def gen_find(filepat,top):
            for path, dirlist, filelist in os.walk(top):
                for name in fnmatch.filter(filelist,filepat):
                    yield os.path.join(path,name)

        def gen_open(filenames):
            for name in filenames:
                yield open(name)

        def gen_cat(sources):
            for s in sources:
                for item in s:
                    yield item

        def get_stack_usage_lines(dir):
            names = gen_find("*.su", os.path.join(dir, "src"))
            files = gen_open(names)
            lines = gen_cat(files)
            return lines

        c.parse_assembly_text("".join(get_assembly_lines(build_dir)))
        for l in get_size_lines(build_dir):
            c.parse_size_line(l)
        for l in get_stack_usage_lines(build_dir):
            c.parse_stack_usage_line(l)

    def all_symbols(self):
        return self.symbols.values()

    def all_functions(self):
        return list([f for f in self.all_symbols() if f.get(TYPE, None) == TYPE_FUNCTION])

@jinja2.contextfilter
def path_filter(context, file_name):
    if context:
        current_file = os.path.dirname(context.parent["file_name"])
        return os.path.relpath(file_name, current_file)
    else:
        return file_name

@jinja2.contextfilter
def symbol_url_filter(context, value):
    file_name = os.path.join(value.get(BASE_FILE, '__builtin'), "symbol_%s.html" % value["name"])
    return path_filter(context, file_name)


class JSONRenderer:

    def __init__(self, collector):
        self.collector = collector

    def render(self):
        data = []
        for symbol in self.collector.all_symbols():
            if symbol.has_key(FILE) and symbol.has_key(LINE):
                entry = {}
                for key in [NAME, BASE_FILE, LINE, STACK_SIZE, SIZE]:
                    if symbol.has_key(key):
                        entry[key] = symbol[key]
                data.append(entry)

        return json.dumps(data, indent=2)

class HTMLRenderer:

    def __init__(self, collector):
        self.collector = collector
        self.template_loader = jinja2.FileSystemLoader(searchpath="templates")
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["symbol_url"] = symbol_url_filter
        self.template_env.filters["path"] = path_filter

        self.template_vars = {
            "symbols": collector.all_symbols(),
            "functions": collector.all_functions(),
            "functions_with_size": list(reversed(sorted([s for s in collector.all_functions() if s.has_key(SIZE)], key=lambda s: s[SIZE])))
        }

    def render_overview(self, file_name):
        return self.render_template("overview.html", file_name)

    def render_template(self, template_name, file_name):
        self.template_vars["file_name"] = file_name
        template = self.template_env.get_template(template_name + ".jinja")
        output = template.render(self.template_vars)
        return output

    def render_symbol(self, symbol, file_name):
        self.template_vars["symbol"] = symbol
        return self.render_template("symbol.html", file_name)

    def render_file(self, file_name):
        return self.render_template("file.html", file_name)

    def copy_static_assets_to_path(self, output_dir):
        css_output = os.path.join(output_dir, "css")
        if os.path.exists(css_output):
            shutil.rmtree(css_output)
        shutil.copytree("templates/css", css_output)

    def render_to_path(self, output_dir):
        # todo: collect files that exist before and delete them afterwards if they hadn't been regenerated

        def ensure_path(p):
            if not os.path.exists(p):
                os.makedirs(p)

        def write(name, content):
            file_name = os.path.join(output_dir, name)
            ensure_path(os.path.dirname(file_name))

            with open(file_name, "w") as f:
                f.write(content)

        ensure_path(output_dir)
        self.copy_static_assets_to_path(output_dir)

        write("index.html", self.render_overview("index.html"))

        # todo: render file overview

        # todo: only render functions
        for s in self.collector.symbols.values():
            file_name = symbol_url_filter(None, s)
            write(file_name, self.render_symbol(s, file_name))


if __name__ == "__main__":
    build_dir = "/Users/behrens/Documents/projects/pebble/puncover/pebble/build"

    c = Collector()
    c.parse_pebble_build_dir(build_dir)
    # pprint(c.symbols)
    # r = HTMLRenderer(c)

    # print(r.render_overview("index.html"))
    # print(r.render_file("puncover.c/index.html"))
    # print(r.render_symbol(c.symbol("puncover.c/main"), "puncover.c/symbol__main.html"))

    # r.render_to_path(os.path.join(build_dir, "puncover"))

    json_renderer = JSONRenderer(c)
    print(json_renderer.render())

