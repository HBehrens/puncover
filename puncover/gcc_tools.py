import os
import subprocess

import itertools


class GCCTools:
    def __init__(self, gcc_base_filename):
        # if base filename is a directory, make sure we have the trailing slash
        if os.path.isdir(gcc_base_filename):
            gcc_base_filename = os.path.join(gcc_base_filename, '')

        self.gcc_base_filename = gcc_base_filename

    def gcc_tool_path(self, name):
        path = self.gcc_base_filename + name
        if os.name == 'nt':
            path+=".exe"
        if not os.path.isfile(path):
            raise Exception("Could not find %s" % path)

        return path

    def gcc_tool_lines(self, name, args, cwd=None):
        proc = subprocess.Popen([self.gcc_tool_path(name)] + args, stdout=subprocess.PIPE, cwd=cwd)
        return [l.decode() for l in proc.stdout.readlines()]

    def get_assembly_lines(self, elf_file):
        return self.gcc_tool_lines('objdump', ['-dslw',  elf_file.name], elf_file.parents[0])

    def get_size_lines(self, elf_file):
        # http://linux.die.net/man/1/nm
        return self.gcc_tool_lines('nm', ['-Sl', elf_file.name], elf_file.parents[0])

    # See https://blog.flameeyes.eu/2010/06/c-name-demangling/ for context
    #
    # This solution courtesy of:
    # https://stackoverflow.com/questions/6526500/c-name-mangling-library-for-python/6526814
    def get_unmangled_names(self, symbol_names, chunk_size=1000):
        # for very long lists we can exceed the maximum length of the command line
        # so we split the names in chunks
        def chunks(l):
            for i in range(0, len(l), chunk_size):
                yield l[i:i + chunk_size]

        lines_list =  [self.gcc_tool_lines('c++filt', c) for c in chunks(symbol_names)]
        lines = list(itertools.chain.from_iterable(lines_list))
        demangled = list(s.rstrip() for s in lines)

        return dict(zip(symbol_names, demangled))
