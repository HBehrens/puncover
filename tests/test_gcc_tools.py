import unittest

from mock import patch

from puncover.gcc_tools import GCCTools


class TestGCCTools(unittest.TestCase):

    def test_chunks_and_rstrip(self):
        t = GCCTools('somePath')
        with patch.object(t, 'gcc_tool_lines') as f:
            f.side_effect = lambda cmd, symbols: [' -%s- ' % s for s in symbols]
            actual = t.get_unmangled_names(['a', 'b', 'c', 'd', 'e'], 2)
            self.assertEqual({'a': ' -a-', 'b': ' -b-', 'c': ' -c-', 'd': ' -d-', 'e': ' -e-'}, actual)
