import unittest
from puncover import Collector

class TestCollector(unittest.TestCase):

    def setUp(self):
        pass

    def test_parses_line(self):
        c = Collector()
        line = "00000550 00000034 T main	/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c:25"
        self.assertTrue(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {'00000550': {
            'file': '/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c',
            'base_file': 'puncover.c',
            'line': 25,
            'name': 'main',
            'size': 52}
        })

    def test_ignores_incomplete_size_line_1(self):
        c = Collector()
        line = "0000059c D __dso_handle"
        self.assertFalse(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {})

    def test_ignores_incomplete_size_line_2(self):
        c = Collector()
        line = "U __preinit_array_end"
        self.assertFalse(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {})

    def test_parses_assembly(self):
        assembly = """
00000098 <pbl_table_addr>:
pbl_table_addr():
  98:	a8a8a8a8 	.word	0xa8a8a8a8

0000009c <__aeabi_dmul>:
__aeabi_dmul():
  9c:	b570      	push	{r4, r5, r6, lr}
"""
        c = Collector()
        self.assertEqual(2, c.parse_assembly_text(assembly))
        self.assertTrue(c.symbols.has_key("0000009c"))
        self.assertEqual(c.symbols["0000009c"]["name"], "__aeabi_dmul")
        self.assertTrue(c.symbols.has_key("00000098"))
        self.assertEqual(c.symbols["00000098"]["name"], "pbl_table_addr")

    def test_stack_usage_line(self):
        line = "puncover.c:14:40:0	16	dynamic,bounded"
        c = Collector()
        c.symbols = {"123": {
            "base_file": "puncover.c",
            "line": 14,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))
        self.assertEqual(16, c.symbols["123"]["stack_size"])
        self.assertEqual("dynamic,bounded", c.symbols["123"]["stack_qualifiers"])

    def test_stack_usage_line2(self):
        line = "puncover.c:8:43:dynamic_stack2	16	dynamic"
        c = Collector()
        c.symbols = {"123": {
            "base_file": "puncover.c",
            "line": 8,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))