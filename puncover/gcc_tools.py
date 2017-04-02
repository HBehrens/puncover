import os
import subprocess


class GCCTools:
    def __init__(self, gcc_base_filename):
        # if base filename is a directory, make sure we have the trailing slash
        if os.path.isdir(gcc_base_filename):
            gcc_base_filename = os.path.join(gcc_base_filename, '')

        self.gcc_base_filename = gcc_base_filename

    def gcc_tool_path(self, name):
        path = self.gcc_base_filename + name
        if not os.path.isfile(path):
            raise Exception("Could not find %s" % path)

        return path

    def gcc_tool_lines(self, name, args, cwd=None):
        proc = subprocess.Popen([self.gcc_tool_path(name)] + args, stdout=subprocess.PIPE, cwd=cwd)
        return proc.stdout.readlines()

    def get_assembly_lines(self, elf_file):
        return self.gcc_tool_lines('objdump', ['-dslw', os.path.basename(elf_file)], os.path.dirname(elf_file))

    def get_size_lines(self, elf_file):
        # http://linux.die.net/man/1/nm
        return self.gcc_tool_lines('nm', ['-Sl', os.path.basename(elf_file)], os.path.dirname(elf_file))

    # See https://blog.flameeyes.eu/2010/06/c-name-demangling/ for context
    #
    # This solution courtesy of:
    # https://stackoverflow.com/questions/6526500/c-name-mangling-library-for-python/6526814
    def get_unmangled_names(self, symbol_names):
        lines = self.gcc_tool_lines('c++filt', symbol_names)
        demangled = list(s.rstrip() for s in lines)

        return dict(zip(symbol_names, demangled))
