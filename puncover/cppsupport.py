import subprocess

# See https://blog.flameeyes.eu/2010/06/c-name-demangling/ for context
#
# This solution courtesy of:
# https://stackoverflow.com/questions/6526500/c-name-mangling-library-for-python/6526814
# (slightly modified to return a dict instead of a list)
def unmangle(names):
    args = ['c++filt']
    args.extend(names)
    pipe = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, _ = pipe.communicate()
    demangled = stdout.split("\n")

    # Each line ends with a newline, so the final entry of the split output
    # will always be ''.
    assert len(demangled) == len(names)+1
    return dict(zip(names, demangled[:-1]))
