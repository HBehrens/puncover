import unittest
from mock import MagicMock
from backtrace_helper import BacktraceHelper
import collector

class TestBacktraceHelper(unittest.TestCase):

    class FakeCollector():
        def __init__(self, symbol_names):
            self.symbol_names = symbol_names

        def symbol(self, name, qualified=True):
            if not qualified and name in self.symbol_names:
                return {collector.NAME: name, collector.TYPE: collector.TYPE_FUNCTION}
            return None

    def setUp(self):
        pass

    def test_returns_empty_list(self):
        r = BacktraceHelper(None)
        self.assertEqual([], r.derive_function_symbols(""))

    def test_returns_known_symbols(self):
        r = BacktraceHelper(TestBacktraceHelper.FakeCollector([
            "codepoint_get_horizontal_advance", "text_walk_lines",
        ]))
        actual = r.derive_function_symbols("""
    fontinfo=0x200010ec <s_system_fonts_info_table+200>) 16 at ../src/fw/applib/graphics/text_resources.c:347
#4  0x08012220 in codepoint_get_horizontal_advance () 16
#5  0x08012602 in walk_line () 112
#6  0x080128d6 in text_walk_lines.constprop.8 () (inlined)
        """)

        self.assertEqual(["codepoint_get_horizontal_advance", "text_walk_lines"], [f[collector.NAME] for f in actual])


    def test_transform_known_symbols(self):
        r = BacktraceHelper(TestBacktraceHelper.FakeCollector([
            "a", "c", "d",
        ]))

        def f(symbol):
            return symbol[collector.NAME] + symbol[collector.NAME]

        actual = r.transform_known_symbols("0 1 a b c d e f 0 2", f)
        self.assertEqual("0 1 aa b cc dd e f 0 2", actual)