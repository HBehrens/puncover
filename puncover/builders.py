import abc
import os
from os.path import dirname
from backtrace_helper import BacktraceHelper
from collector import CALLERS
from collector import CALLEES


class Builder:

    def __init__(self, collector, src_root):
        self.files = {}
        self.collector = collector
        self.backtrace_helper = BacktraceHelper(collector)
        self.src_root = src_root

    def store_file_time(self, path, store_empty=False):
        self.files[path] = 0 if store_empty else os.path.getmtime(path)

    def build(self):
        for f in self.files.keys():
            self.store_file_time(f)
        self.collector.reset()
        self.do_parse()
        self.enhance()

    def needs_build(self):
        return any([os.path.getmtime(f) > t for f,t in self.files.items()])

    def build_if_needed(self):
        if self.needs_build():
            self.build()

    @abc.abstractmethod
    def do_parse(self):
        pass

    def enhance(self):
        self.collector.enhance(self.src_root)
        for f in self.collector.all_functions():
            if len(f[CALLERS]) == 0:
                self.backtrace_helper.deepest_callee_tree(f)

            if len(f[CALLEES]) == 0:
                self.backtrace_helper.deepest_caller_tree(f)


class PebbleProjectBuilder(Builder):
    def __init__(self, collector, src_root, project_dir):
        # TODO: check if this is a pebble project dir
        Builder.__init__(self, collector, src_root if src_root else project_dir)
        self.project_dir = project_dir
        self.store_file_time(self.elf_path(), store_empty=True)

    def elf_path(self):
        return os.path.join(self.project_dir, 'build', 'pebble-app.elf')

    def su_dir(self):
        return os.path.join(self.project_dir, "build", "src")

    def do_parse(self):
        self.collector.parse(self.elf_path(), self.su_dir())


class ElfBuilder(Builder):

    def __init__(self, collector, src_root, elf_file, su_dir):
        Builder.__init__(self, collector, src_root if src_root else dirname(dirname(elf_file)))
        self.store_file_time(elf_file, store_empty=True)
        self.elf_file = elf_file
        self.su_dir = su_dir

    def do_parse(self):
        self.collector.parse(self.elf_file, self.su_dir)