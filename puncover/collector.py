import fnmatch
import os
import re
import sys
import pathlib

NAME = "name"
DISPLAY_NAME = "display_name"
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

PYTHON_VER = {"major": sys.version_info[0], "minor": sys.version_info[1]}

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

    def __init__(self, gcc_tools):
        self.gcc_tools = gcc_tools
        self.symbols = {}
        self.file_elements = {}
        self.symbols_by_qualified_name = None
        self.symbols_by_name = None

    def reset(self):
        self.symbols = {}
        self.file_elements = {}
        self.symbols_by_qualified_name = None
        self.symbols_by_name = None

    def qualified_symbol_name(self, symbol):
        if BASE_FILE in symbol:
            html_path = pathlib.Path.joinpath(symbol[PATH], symbol[NAME])
            return str(html_path)
        return symbol[NAME]

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
        if NAME in sym and sym[NAME] != name:
            # warning("Name for symbol at %s inconsistent (was '%s', now '%s')" % (address, sym[NAME], name))
            pass
        else:
            sym[NAME] = name
        if size:
            sym[SIZE] = int(size)
        if file:
            sym[PATH] = pathlib.Path(file)
            sym[BASE_FILE] = sym[PATH].name
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
    if os.name == 'nt':
        parse_size_line_re = re.compile(r"^([\da-f]{8})\s+([\da-f]{8})\s+(.)\s+(\w+)(\s+([a-zA-Z]:.+)):(\d+)?")
    else:
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

        types = {"A": TYPE_FUNCTION, "T": TYPE_FUNCTION, "D": TYPE_VARIABLE, "B": TYPE_VARIABLE, "R": TYPE_VARIABLE}

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
    parse_stack_usage_line_pattern = re.compile(r"^(.*?\.[ch](pp)?):(\d+):(\d+):([^\t]+)\t+(\d+)\s+([a-z,]+)")

    def parse_stack_usage_line(self, line):
        match = self.parse_stack_usage_line_pattern.match(line)
        if not match:
            return False

        file = pathlib.Path(match.group(1))
        base_file_name = file.name
        line = int(match.group(3))
        symbol_name = match.group(5)
        stack_size = int(match.group(6))
        stack_qualifier = match.group(7)

        return self.add_stack_usage(base_file_name, line, symbol_name, stack_size, stack_qualifier)

    # TODO: handle operators, e.g. String::operator=(char const*)
    # TODO: handle templates, e.g. void LinkedList<T>::clear() [with T = Loggable]
    re_cpp_display_name = re.compile(r"^(\w[^\(\s]*\s)*(\w+::~?)?(\w+)(\([^\)]*\))?(\sconst)?$")

    def display_name_simplified(self, name):
        # .su files have elements such as "virtual size_t Print::write(const uint8_t*, size_t)"
        # c++filt gives us "Print::write(unsigned char const*, unsigned int)"

        m = self.re_cpp_display_name.match(name)
        if m:
            groups = list(m.groups(''))

            def replace_identifiers(m):
                # these values were derived from an ARM 32Bit target
                # it could be that they need further adjustments
                # yes, we are treating int as long works only for 32bit platforms
                # right now, our sample projects use both types unpredictably in the same binary (oh, dear)
                mapping = {
                    'const': '', # we ignore those as a feasible simplification
                    'size_t': 'unsigned long',
                    'uint8_t': 'unsigned char',
                    'int8_t': 'signed char',
                    'uint16_t': 'unsigned short',
                    'int16_t': 'short',
                    'uint32_t': 'unsigned long',
                    'int32_t': 'long',
                    'uint64_t': 'unsigned long long',
                    'int64_t': 'long long',
                    'byte': 'unsigned char',
                    'int': 'long',
                }

                return mapping.get(m.group(), m.group())

            # in case, we have parameters, simplify those
            groups[3] = re.sub(r'\w+', replace_identifiers, groups[3])

            # TODO: C allows you to write the same C types in many different notations
            # http://ieng9.ucsd.edu/~cs30x/Std.C/types.html#Basic%20Integer%20Types
            # applies to tNMEA2000::SetProductInformation or Print::printNumber

            # remove leading "virtual size_t" etc.
            # non-matching groups should be empty strings
            name = ''.join(groups[1:])

        # remove white space artifacts from previous replacements
        for k, v in [('   ', ' '), ('  ', ' '), ('( ', '('), (' )', ')'), ('< ', '<'), (' >', '>'), (' *', '*'), (' &', '&')]:
            name = name.replace(k, v)

        return name

    def display_names_match(self, a, b):
        if a is None or b is None:
            return False

        if a == b:
            return True

        simplified_a = self.display_name_simplified(a)
        simplified_b = self.display_name_simplified(b)
        return simplified_a == simplified_b

    def add_stack_usage(self, base_file_name, line, symbol_name, stack_size, stack_qualifier):
        basename_symbols = [s for s in self.symbols.values() if s.get(BASE_FILE, None) == base_file_name]
        for symbol in basename_symbols:

            if symbol.get(LINE, None) == line or self.display_names_match(symbol_name, symbol.get(DISPLAY_NAME, None)):
                symbol[STACK_SIZE] = stack_size
                symbol[STACK_QUALIFIERS] = stack_qualifier
                return True

        # warning("Couldn't find symbol for %s:%d:%s" % (base_file_name, line, symbol_name))
        return False

    windows_path_pattern = re.compile(r"^([a-zA-Z]+)(:)(\\)(.+)$")
    
    def normalize_files_paths(self, base_dir):
        base_dir = os.path.abspath(base_dir) if base_dir else pathlib.Path(".")
        for s in self.all_symbols():
            path = s.get(PATH, None)
            if path:
                str_path = str(path)
                abs_win_path = self.windows_path_pattern.match(str_path)
                if base_dir in path.parents:
                    path = path.relative_to(base_dir)
                # Remove root from path
                elif str_path.startswith("/"):
                    str_path = str_path[1:]
                    path = pathlib.Path(str_path)
                elif abs_win_path:
                    # prefix drive letter 
                    # in the rare case where there are two
                    # files with same path and different drive letter
                    drive_letter = abs_win_path.group(1)
                    str_path = abs_win_path.group(1)+"_"+abs_win_path.group(4)
                    path = pathlib.Path(str_path)
                s[PATH] = path

    def unmangle_cpp_names(self):
        symbol_names = list(symbol[NAME] for symbol in self.all_symbols())

        unmangled_names = self.gcc_tools.get_unmangled_names(symbol_names)

        for s in self.all_symbols():
            s[DISPLAY_NAME] = unmangled_names[s[NAME]]

    def parse_elf(self, elf_file):

        print("parsing ELF at %s" % elf_file)

        self.parse_assembly_text("".join(self.gcc_tools.get_assembly_lines(elf_file)))
        for l in self.gcc_tools.get_size_lines(elf_file):
            self.parse_size_line(l)

        self.elf_mtime = os.path.getmtime(elf_file)

    def parse_su_dir(self, su_dir):

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

        if su_dir:
            print("parsing stack usages starting at %s" % su_dir)
            for l in get_stack_usage_lines(su_dir):
                self.parse_stack_usage_line(l)

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
            if ASM in symbol:
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
            return len(match.group(1).replace(" ", "")) // 2
        return 0

    def enhance_function_size_from_assembly(self):
        for f in self.all_symbols():
            if ASM in f:
                f[SIZE] = sum([self.count_assembly_code_bytes(l) for l in f[ASM]])

    def enhance_sibling_symbols(self):
        for f in self.all_functions():
            if SIZE in f:
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
            unknown_path = pathlib.Path("<unknown>/<unknown>")
            p = s.get(PATH, unknown_path)
            if p != unknown_path:
                posix_root_path = str(p).startswith("\\")
                windows_os = os.name == "nt"
                # Detects if parsing posix paths in elf in a windows machine
                win_parsing_posix = windows_os and posix_root_path
                if not win_parsing_posix:
                    resolved_path = p.resolve(strict=False)
                else:
                    resolved_path = p
                if windows_os and PYTHON_VER["major"]==3 and PYTHON_VER["minor"]<10:
                    pathlib_prepends_cwd = False
                else:
                    pathlib_prepends_cwd = True
                    
                if (not p.is_absolute() 
                    and not win_parsing_posix
                    and pathlib_prepends_cwd): 
                    # pathlib prepends cwd if it couldnt 
                    # resolve locally the file
                    cwd = pathlib.Path().absolute()
                    p = resolved_path.relative_to(cwd)
                else:
                    p = resolved_path
            s[PATH] = p
            s[BASE_FILE] = p.name
            s[FILE] = self.file_for_path(p)
            s[FILE][SYMBOLS].append(s)

    def file_element_for_path(self, path, type, default_values):
        if not path:
            return None

        result = self.file_elements.get(path, None)
        if not result:
            parent_len = len(path.parents)
            if parent_len > 0:
                parent_dir = path.parents[0]
            else:
                parent_dir = path
            parent_available = parent_len > 0 and parent_dir != pathlib.Path(".")
            parent_folder = self.folder_for_path(parent_dir) if parent_available else None 
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
