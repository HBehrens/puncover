from __future__ import print_function
import fnmatch
import json
import os
import re
import subprocess
import sys

NAME = "name"
SIZE = "size"
PATH = "path"
BASE_FILE = "base_file"
LINE = "line"
ASM = "asm"
STACK_SIZE = "stack_size"
STACK_QUALIFIERS = "stack_qualifiers"
ADDRESS = "address"
TYPE = "type"
TYPE_FUNCTION = "function"
TYPE_VARIABLE = "variable"
TYPE_FILE = "file"
TYPE_FOLDER = "folder"
PREV_FUNCTION = "prev_function"
NEXT_FUNCTION = "next_function"
FUNCTIONS = "functions"
VARIABLES = "variables"
SYMBOLS = "symbols"
FILE = "file"
FILES = "files"
FOLDER = "folder"
ROOT = "root"
SUB_FOLDERS = "sub_folders"
COLLAPSED_NAME = "collapsed_name"
COLLAPSED_SUB_FOLDERS = "collapsed_sub_folders"

def warning(*objs):
    print("WARNING: ", *objs, file=sys.stderr)


def left_strip_from_list(lines):
    if len(lines) <= 0:
        return lines

    # detect longest common sequence of white spaces
    longest_match = re.match(r"^\s*", lines[0]).group(0)


    for line in lines:
        while not line.startswith(longest_match):
            longest_match = longest_match[:-1]

    # remove from each string
    return list([line[len(longest_match):] for line in lines])


class Collector:

    def __init__(self, pebble_sdk=None):
        self.symbols = {}
        self.file_elements = {}
        self.pebble_sdk = pebble_sdk

    def as_dict(self):
        return {
            "symbols" : self.symbols,
            "pebble_sdk" : self.pebble_sdk,
        }

    def save_to_json(self, filename):
        with open(filename, "w") as f:
            json.dump(self.as_dict(), f, indent=2, sort_keys=True)

    def from_dict(self, dict):
        self.symbols = dict.get("symbols", {})
        self.pebble_sdk = dict.get("pebble_sdk", None)

    def load_from_json(self, filename):
        with open(filename) as f:
            self.from_dict(json.load(f))

    def qualified_symbol_name(self, symbol):
        return os.path.join(symbol[PATH], symbol[NAME]) if symbol.has_key(BASE_FILE) else symbol[NAME]

    def symbol(self, name, qualified=True):
        for s in self.symbols.values():
            if self.qualified_symbol_name(s) == name or (not qualified and s[NAME] == name):
                return s
        return None

    def symbol_by_addr(self, addr):
        addr = int(addr, 16)
        for s in self.symbols.values():
            if int(s[ADDRESS],16) == addr:
                return s
        return None

    def add_symbol(self, name, address, size=None, file=None, line=None, assembly_lines=None, type=None):
        sym = self.symbols.get(address, {})
        if sym.has_key(NAME) and sym[NAME] != name:
            warning("Name for symbol at %s inconsistent (was '%s', now '%s')" % (address, sym[NAME], name))
        else:
            sym[NAME] = name
        if size:
            sym[SIZE] = int(size)
        if file:
            sym[PATH] = file
            sym[BASE_FILE] = os.path.basename(file)
        if line:
            sym[LINE] = line
        if assembly_lines:
            assembly_lines = left_strip_from_list(assembly_lines)

            sym[ASM] = assembly_lines
            sym[TYPE] = TYPE_FUNCTION
        if type:
            sym[TYPE] = type

        sym[ADDRESS] = address

        self.symbols[address] = sym

    def parse_size_line(self, line, base_dir="/"):
        # print(line)
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
            if file.startswith(base_dir):
                file = os.path.relpath(file, base_dir)
            line = int(match.group(7))
        else:
            file = None
            line = None

        types = {"T": TYPE_FUNCTION, "D": TYPE_VARIABLE, "B": TYPE_VARIABLE}

        self.add_symbol(name, address=addr, size=size, file=file, line=line, type = types.get(type.upper(), None))

        return True

    def parse_assembly_text(self, assembly):
        # print(assembly)
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
        # 00000098 <pbl_table_addr.constprop.0>:
        function_start_pattern = re.compile(r"^([\da-f]{8})\s+<(\w+)(\..*)?>:")

        # /Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c:8
        c_reference_pattern = re.compile(r"^[^:]+:\d+\s*")
        for line in assembly.split("\n"):
            match = function_start_pattern.match(line)
            if match:
                found_symbols += flush_current_symbol()
                addr = match.group(1)
                name = match.group(2)
                assembly_lines = []
            else:
                if not c_reference_pattern.match(line) and line.strip() != "":
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


    def parse(self, elf_file, su_dir):
        def in_pebble_sdk(name):
            return os.path.join(self.pebble_sdk, 'arm-cs-tools/bin', name) if self.pebble_sdk else name

        def get_assembly_lines(elf_file):
            proc = subprocess.Popen([in_pebble_sdk('arm-none-eabi-objdump'),'-dslw', os.path.basename(elf_file)], stdout=subprocess.PIPE, cwd=os.path.dirname(elf_file))
            # proc = subprocess.Popen([in_pebble_sdk('arm-none-eabi-objdump'),'-d', os.path.basename(elf_file)], stdout=subprocess.PIPE, cwd=os.path.dirname(elf_file))
            return proc.stdout.readlines()


        def get_size_lines(elf_file):
            # http://linux.die.net/man/1/nm
            proc = subprocess.Popen([in_pebble_sdk('arm-none-eabi-nm'),'-Sl', os.path.basename(elf_file)], stdout=subprocess.PIPE, cwd=os.path.dirname(elf_file))
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

        def get_stack_usage_lines(su_dir):
            names = gen_find("*.su", su_dir)
            files = gen_open(names)
            lines = gen_cat(files)
            return lines

        print("parsing ELF at %s" % elf_file)

        self.parse_assembly_text("".join(get_assembly_lines(elf_file)))
        for l in get_size_lines(elf_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(elf_file)))
            self.parse_size_line(l, base_dir)

        for l in get_stack_usage_lines(su_dir):
            self.parse_stack_usage_line(l)

    def parse_pebble_project_dir(self, project_dir):
        elf_file = os.path.join(project_dir, 'build', 'pebble-app.elf')
        su_dir = os.path.join(project_dir, "build", "src")
        self.parse(elf_file, su_dir)

    def sorted_by_size(self, symbols):
        return sorted(symbols, key=lambda k: k.get("size", 0), reverse=True)

    def all_symbols(self):
        return self.sorted_by_size(self.symbols.values())

    def all_functions(self):
        return list([f for f in self.all_symbols() if f.get(TYPE, None) == TYPE_FUNCTION])

    def all_variables(self):
        return list([f for f in self.all_symbols() if f.get(TYPE, None) == TYPE_VARIABLE])

    def enhance_assembly(self):
        for key, symbol in self.symbols.items():
            if symbol.has_key(ASM):
                symbol[ASM] = list([self.enhanced_assembly_line(l) for l in symbol[ASM]])

    def add_function_call(self, caller, callee):
        if caller != callee:
            if not callee in caller["callees"]:
                caller["callees"].append(callee)
            if not caller in callee["callers"]:
                callee["callers"].append(caller)

    def enhance_call_tree_from_assembly_line(self, function, line):
        #  934:	f7ff bba8 	b.w	88 <jump_to_pbl_function>
        # 8e4:	f000 f824 	bl	930 <app_log>
        #
        # but not:
        # 805bbac:	2471 0805 b64b 0804 b3c9 0804 b459 0804     q$..K.......Y...


        pattern = re.compile(r"^\s*[\da-f]+:\s+[\d\sa-f]{9}\s+BL?(EQ|NE|CS|HS|CC|LO|MI|PL|VS|VC|HI|LS|GE|LT|GT|LE|AL)?(\.W|\.N)?\s+([\d\sa-f]+)", re.IGNORECASE)

        match = pattern.match(line)

        if match:
            callee = self.symbol_by_addr(match.group(3))
            if callee:
                self.add_function_call(function, callee)
                return True

        return False

    def enhance_call_tree(self):
        for f in self.all_functions():
            for k in ["callers", "callees"]:
                f[k] = f.get(k, [])

        for f in self.all_functions():
            if f.has_key(ASM):
                [self.enhance_call_tree_from_assembly_line(f, l) for l in f[ASM]]

        for f in self.all_functions():
            for k in ["callers", "callees"]:
                f[k] = self.sorted_by_size(f[k])

    def enhance(self):
        self.enhance_function_size_from_assembly()
        self.enhance_assembly()
        self.enhance_call_tree()
        self.enhance_sibling_symbols()
        self.derive_folders()
        self.enhance_file_elements()

    def enhanced_assembly_line(self, line):
        #   98: a8a8a8a8  bl 98
        pattern = re.compile(r"^\s*[\da-f]+:\s+[\d\sa-f]{9}\s+bl\s+([\d\sa-f]+)\s*$")
        match = pattern.match(line)
        if match:
            symbol = self.symbol_by_addr(match.group(1))
            if symbol:
                return line+ " <%s>" % (symbol["name"])
        return line

    def count_assembly_code_bytes(self, line):
        # 88a:	ebad 0d03 	sub.w	sp, sp, r3
        pattern = re.compile(r"^\s*[\da-f]+:\s+([\d\sa-f]{9})")
        match = pattern.match(line)
        if match:
            return len(match.group(1).replace(" ", "")) / 2
        return 0

    def enhance_function_size_from_assembly(self):
        for f in self.all_symbols():
            if f.has_key(ASM):
                f[SIZE] = sum([self.count_assembly_code_bytes(l) for l in f[ASM]])

    def enhance_sibling_symbols(self):
        for f in self.all_functions():
            if f.has_key(SIZE):
                addr = int(f.get(ADDRESS), 16) + f.get(SIZE)
                next_symbol = self.symbol_by_addr(hex(addr))
                if next_symbol and next_symbol.get(TYPE, None) == TYPE_FUNCTION:
                    f[NEXT_FUNCTION] = next_symbol

        for f in self.all_functions():
            n = f.get(NEXT_FUNCTION, None)
            if n:
                n[PREV_FUNCTION] = f

    def derive_folders(self):
        for s in self.all_symbols():
            p = s.get(PATH, None)
            if p:
                p = os.path.normpath(p)
                s[PATH] = p
                s[FILE] = self.file_for_path(p)
                s[FILE][SYMBOLS].append(s)

    def file_element_for_path(self, path, type, default_values):
        if not path:
            return None

        result = self.file_elements.get(path, None)
        if not result:
            parent_dir = os.path.dirname(path)
            parent_folder = self.folder_for_path(parent_dir) if parent_dir and parent_dir != "/" else None
            result = {
                TYPE: type,
                PATH: path,
                FOLDER: parent_folder,
                NAME: os.path.basename(path),
            }
            for k, v in default_values.items():
                result[k] = v
            self.file_elements[path] = result

        return result if result[TYPE] == type else None

    def file_for_path(self, path):
        return self.file_element_for_path(path, TYPE_FILE, {SYMBOLS:[]})

    def folder_for_path(self, path):
        return self.file_element_for_path(path, TYPE_FOLDER, {FILES:[], SUB_FOLDERS:[], COLLAPSED_SUB_FOLDERS:[]})

    def file_items_ancestors(self, item):
        while item.get(FOLDER):
            item = item[FOLDER]
            yield item

    def enhance_file_elements(self):
        for f in self.all_files():
            parent = f.get(FOLDER, None)
            if parent:
                parent[FILES].append(f)

            f[SYMBOLS] = sorted(f[SYMBOLS], key=lambda s: s[NAME])
            f[FUNCTIONS] = list([s for s in f[SYMBOLS] if s.get(TYPE, None) == TYPE_FUNCTION])
            f[VARIABLES] = list([s for s in f[SYMBOLS] if s.get(TYPE, None) == TYPE_VARIABLE])

        for f in self.all_folders():
            parent = f.get(FOLDER, None)
            if parent:
                parent[SUB_FOLDERS].append(f)
            ancestors = list(self.file_items_ancestors(f))
            if len(ancestors) > 0:
                f[ROOT] = ancestors[-1]

            collapsed_name = f[NAME]
            for a in ancestors:
                if len(f[FILES]) > 0:
                    a[COLLAPSED_SUB_FOLDERS].append(f)
                if len(a[FILES]) > 0:
                    break
                collapsed_name = os.path.join(a[NAME], collapsed_name)
            f[COLLAPSED_NAME] = collapsed_name

        for f in self.all_folders():
            for k in [FILES, SUB_FOLDERS]:
                f[k] = sorted(f[k], key=lambda s: s[NAME])
            f[COLLAPSED_SUB_FOLDERS] = sorted(f[COLLAPSED_SUB_FOLDERS], key=lambda s: s[COLLAPSED_NAME])

    def all_files(self):
        return [f for f in self.file_elements.values() if f[TYPE] == TYPE_FILE]

    def all_folders(self):
        return [f for f in self.file_elements.values() if f[TYPE] == TYPE_FOLDER]

    def root_folders(self):
        return [f for f in self.all_folders() if not f[FOLDER]]

    def collapsed_root_folders(self):
        result = []

        def non_empty_leafs(f):
            if len(f[FILES]) > 0:
                result.append(f)
            else:
                for s in f[SUB_FOLDERS]:
                    non_empty_leafs(s)

        for f in self.root_folders():
            non_empty_leafs(f)

        return result

