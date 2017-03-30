from __future__ import print_function
import fnmatch
import json
import os
import re
import subprocess
import sys
from __builtin__ import any

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
ANCESTORS = "ancestors"
SUB_FOLDERS = "sub_folders"
COLLAPSED_NAME = "collapsed_name"
COLLAPSED_SUB_FOLDERS = "collapsed_sub_folders"
CALLEES = "callees"
CALLERS = "callers"

DEEPEST_CALLEE_TREE = "deepest_callee_tree"
DEEPEST_CALLER_TREE = "deepest_caller_tree"

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

    def __init__(self, arm_tools_dir=None):
        self.arm_tools_dir = arm_tools_dir
        self.symbols = {}
        self.file_elements = {}
        self.symbols_by_qualified_name = None
        self.symbols_by_name = None

    def reset(self):
        self.symbols = {}
        self.file_elements = {}
        self.symbols_by_qualified_name = None
        self.symbols_by_name = None

    def as_dict(self):
        return {
            "symbols" : self.symbols,
            "arm_tools_dir" : self.arm_tools_dir,
        }

    def save_to_json(self, filename):
        with open(filename, "w") as f:
            json.dump(self.as_dict(), f, indent=2, sort_keys=True)

    def from_dict(self, dict):
        self.symbols = dict.get("symbols", {})
        self.arm_tools_dir = dict.get("arm_tools_dir", None)

    def load_from_json(self, filename):
        with open(filename) as f:
            self.from_dict(json.load(f))

    def arm_tool(self, name):
        if not self.arm_tools_dir:
            raise Exception("ARM tools directory not set")

        path = os.path.join(self.arm_tools_dir, 'bin', name)
        if not os.path.isfile(path):
            raise Exception("Could not find %s" % path)

        return path

    def qualified_symbol_name(self, symbol):
        return os.path.join(symbol[PATH], symbol[NAME]) if symbol.has_key(BASE_FILE) else symbol[NAME]

    def symbol(self, name, qualified=True):
        self.build_symbol_name_index()

        index = self.symbols_by_qualified_name if qualified else self.symbols_by_name
        return index.get(name, None)

    def symbol_by_addr(self, addr):
        int_addr = int(addr, 16)
        return self.symbols.get(int_addr, None)

    def add_symbol(self, name, address, size=None, file=None, line=None, assembly_lines=None, type=None, stack_size=None):
        int_address = int(address, 16)
        sym = self.symbols.get(int_address, {})
        if sym.has_key(NAME) and sym[NAME] != name:
            # warning("Name for symbol at %s inconsistent (was '%s', now '%s')" % (address, sym[NAME], name))
            pass
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
        if stack_size:
            sym[STACK_SIZE] = stack_size

        sym[ADDRESS] = address

        self.symbols[int_address] = sym
        return sym

    # 00000550 00000034 T main	/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c:25
    parse_size_line_re = re.compile(r"^([\da-f]{8})\s+([\da-f]{8})\s+(.)\s+(\w+)(\s+([^:]+):(\d+))?")

    def parse_size_line(self, line):
        # print(line)
        match = self.parse_size_line_re.match(line)
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

        types = {"T": TYPE_FUNCTION, "D": TYPE_VARIABLE, "B": TYPE_VARIABLE, "R": TYPE_VARIABLE}

        self.add_symbol(name, address=addr, size=size, file=file, line=line, type = types.get(type.upper(), None))

        return True

    # 00000098 <pbl_table_addr>:
    # 00000098 <pbl_table_addr.constprop.0>:
    parse_assembly_text_function_start_pattern = re.compile(r"^([\da-f]{8})\s+<(\.?\w+)(\..*)?>:")

    # /Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c:8
    parse_assembly_text_c_reference_pattern = re.compile(r"^(/[^:]+)(:(\d+))?")

    def parse_assembly_text(self, assembly):
        # print(assembly)
        name = None
        addr = None
        symbol_file = None
        symbol_line = None
        assembly_lines = []
        found_symbols = 0

        def flush_current_symbol():
            if name and addr:
                self.add_symbol(name, addr, assembly_lines=assembly_lines, file=symbol_file, line=symbol_line)
                return 1
            return 0

        for line in assembly.split("\n"):
            match = self.parse_assembly_text_function_start_pattern.match(line)
            if match:
                found_symbols += flush_current_symbol()
                addr = match.group(1)
                name = match.group(2)
                symbol_file = None
                symbol_line = None
                assembly_lines = []
            else:
                file_match = self.parse_assembly_text_c_reference_pattern.match(line)
                if not file_match and line.strip() != "":
                    assembly_lines.append(line)
                elif file_match and not symbol_file:
                    symbol_file = file_match.group(1)
                    if file_match.group(3):
                        symbol_line = int(file_match.group(3))

        found_symbols += flush_current_symbol()
        return found_symbols

    # puncover.c:8:43:dynamic_stack2	16	dynamic
    # puncover.c:14:40:0	16	dynamic,bounded
    # puncover.c:8:43:dynamic_stack2	16	dynamic
    parse_stack_usage_line_pattern = re.compile(r"^(.*?\.c):(\d+):(\d+):([^\s]+)\s+(\d+)\s+([a-z,]+)")

    def parse_stack_usage_line(self, line):
        match = self.parse_stack_usage_line_pattern.match(line)
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

        # warning("Couldn't find symbol for %s:%d:%s" % (base_file_name, line, symbol_name))
        return False


    def normalize_files_paths(self, base_dir):
        base_dir = os.path.abspath(base_dir) if base_dir else "/"

        for s in self.all_symbols():
            path = s.get(PATH, None)
            if path:
                if path.startswith(base_dir):
                    path = os.path.relpath(path, base_dir)
                elif path.startswith("/"):
                    path = path[1:]
                s[PATH] = path

    # See https://blog.flameeyes.eu/2010/06/c-name-demangling/ for context
    #
    # This solution courtesy of:
    # https://stackoverflow.com/questions/6526500/c-name-mangling-library-for-python/6526814
    def unmangle_cpp_names(self):
        symbol_names = list(symbol['name'] for symbol in self.all_symbols())

        proc = subprocess.Popen([ self.arm_tool('arm-none-eabi-c++filt') ] + symbol_names, stdout=subprocess.PIPE)
        demangled = list(s.rstrip() for s in proc.stdout.readlines())

        unmangled_names = dict(zip(symbol_names, demangled))

        for s in self.all_symbols():
            s['display_name'] = unmangled_names[s['name']]

    def parse(self, elf_file, su_dir):
        def get_assembly_lines(elf_file):
            proc = subprocess.Popen([self.arm_tool('arm-none-eabi-objdump'),'-dslw', os.path.basename(elf_file)], stdout=subprocess.PIPE, cwd=os.path.dirname(elf_file))
            # proc = subprocess.Popen([in_pebble_sdk('arm-none-eabi-objdump'),'-d', os.path.basename(elf_file)], stdout=subprocess.PIPE, cwd=os.path.dirname(elf_file))
            return proc.stdout.readlines()


        def get_size_lines(elf_file):
            # http://linux.die.net/man/1/nm
            proc = subprocess.Popen([self.arm_tool('arm-none-eabi-nm'),'-Sl', os.path.basename(elf_file)], stdout=subprocess.PIPE, cwd=os.path.dirname(elf_file))
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
            self.parse_size_line(l)

        self.elf_mtime = os.path.getmtime(elf_file)

        if su_dir:
            print("parsing stack usages starting at %s" % su_dir)
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
            if not callee in caller[CALLEES]:
                caller[CALLEES].append(callee)
            if not caller in callee[CALLERS]:
                callee[CALLERS].append(caller)
                caller_file = caller.get("file", None)
                callee_file = callee.get("file", None)
                if callee_file and caller_file and callee_file != caller_file:
                    callee["called_from_other_file"] = True

    #  934:	f7ff bba8 	b.w	88 <jump_to_pbl_function>
    # 8e4:	f000 f824 	bl	930 <app_log>
    #
    # but not:
    # 805bbac:	2471 0805 b64b 0804 b3c9 0804 b459 0804     q$..K.......Y...
    enhance_call_tree_pattern = re.compile(r"^\s*[\da-f]+:\s+[\d\sa-f]{9}\s+BL?(EQ|NE|CS|HS|CC|LO|MI|PL|VS|VC|HI|LS|GE|LT|GT|LE|AL)?(\.W|\.N)?\s+([\d\sa-f]+)", re.IGNORECASE)

    def enhance_call_tree_from_assembly_line(self, function, line):
        if "<" not in line:
            return False

        match = self.enhance_call_tree_pattern.match(line)

        if match:
            callee = self.symbol_by_addr(match.group(3))
            if callee:
                self.add_function_call(function, callee)
                return True

        return False

    def enhance_call_tree(self):
        for f in self.all_functions():
            for k in [CALLERS, CALLEES]:
                f[k] = f.get(k, [])

        for f in self.all_functions():
            if ASM in f:
                [self.enhance_call_tree_from_assembly_line(f, l) for l in f[ASM]]

    def enhance(self, src_root):
        self.normalize_files_paths(src_root)
        print("enhancing function sizes")
        self.enhance_function_size_from_assembly()
        print("deriving folders")
        self.derive_folders()
        print("enhancing file elements")
        self.enhance_file_elements()
        print("enhancing assembly")
        self.enhance_assembly()
        print("enhancing call tree")
        self.enhance_call_tree()
        print("enhancing siblings")
        self.enhance_sibling_symbols()
        self.enhance_symbol_flags()
        print("unmangling c++ symbols")
        self.unmangle_cpp_names()

    #   98: a8a8a8a8  bl 98
    enhanced_assembly_line_pattern = re.compile(r"^\s*[\da-f]+:\s+[\d\sa-f]{9}\s+bl\s+([\d\sa-f]+)\s*$")

    def enhanced_assembly_line(self, line):
        match = self.enhanced_assembly_line_pattern.match(line)
        if match:
            symbol = self.symbol_by_addr(match.group(1))
            if symbol:
                return line+ " <%s>" % (symbol["name"])
        return line

    # 88a:	ebad 0d03 	sub.w	sp, sp, r3
    count_assembly_code_bytes_re = re.compile(r"^\s*[\da-f]+:\s+([\d\sa-f]{9})")

    def count_assembly_code_bytes(self, line):
        match = self.count_assembly_code_bytes_re.match(line)
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
            p = s.get(PATH, "<unknown>/<unknown>")
            p = os.path.normpath(p)
            s[PATH] = p
            s[BASE_FILE] = os.path.basename(p)
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
            f[ANCESTORS] = ancestors
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

    def enhance_symbol_flags(self):
        is_float_function_pattern = re.compile(r"^__aeabi_(f.*|.*2f)|__addsf3$")
        def is_float_function_name(n):
            return is_float_function_pattern.match(n)

        float_functions = [f for f in self.all_functions() if is_float_function_name(f[NAME])]
        for f in self.all_functions():
            callees = f[CALLEES]
            f["calls_float_function"] = any([ff in callees for ff in float_functions])

        for file in self.all_files():
            file["calls_float_function"] = any([f["calls_float_function"] for f in file[FUNCTIONS]])


        def folder_calls_float_function(folder):
            result = any([f["calls_float_function"] for f in folder[FILES]])
            for sub_folder in folder[SUB_FOLDERS]:
                if folder_calls_float_function(sub_folder):
                    result = True
            folder["calls_float_function"] = result
            return result

        for folder in self.root_folders():
            folder_calls_float_function(folder)

    def build_symbol_name_index(self):
        if not self.symbols_by_name or not self.symbols_by_qualified_name:
            self.symbols_by_name = {}
            self.symbols_by_qualified_name = {}

            for s in self.symbols.values():
                name = s[NAME]
                if name:
                    self.symbols_by_name[name] = s

                qualified_name = self.qualified_symbol_name(s)
                if qualified_name:
                    self.symbols_by_qualified_name[qualified_name] = s
