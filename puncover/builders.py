import abc
import os
from os.path import dirname
from puncover.backtrace_helper import BacktraceHelper


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
        self.collector.parse_elf(self.get_elf_path())
        self.collector.enhance(self.src_root)
        self.collector.parse_su_dir(self.get_su_dir())
        self.build_call_trees()

    def needs_build(self):
        return any([os.path.getmtime(f) > t for f,t in self.files.items()])

    def build_if_needed(self):
        if self.needs_build():
            self.build()

    @abc.abstractmethod
    def get_elf_path(self):
        pass

    @abc.abstractmethod
    def get_su_dir(self):
        pass

    def build_call_trees(self):
        for f in self.collector.all_functions():
            self.backtrace_helper.deepest_callee_tree(f)
            self.backtrace_helper.deepest_caller_tree(f)


class ElfBuilder(Builder):

    def __init__(self, collector, src_root, elf_file, su_dir):
        Builder.__init__(self, collector, src_root if src_root else dirname(dirname(elf_file)))
        self.store_file_time(elf_file, store_empty=True)
        self.elf_file = elf_file
        self.su_dir = su_dir

    def get_elf_path(self):
        return self.elf_file

    def get_su_dir(self):
        return self.su_dir
