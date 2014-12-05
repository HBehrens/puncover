import unittest
from collector import Collector, left_strip_from_list
from mock import patch
import collector


class TestCollector(unittest.TestCase):

    def setUp(self):
        pass

    def test_left_strip_from_list(self):
        self.assertEqual(left_strip_from_list(["  a", "   b"]), ["a", " b"])

    def test_parses_function_line(self):
        c = Collector()
        line = "00000550 00000034 T main	/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c:25"
        self.assertTrue(c.parse_size_line(line))
        print c.symbols
        self.assertDictEqual(c.symbols, {'00000550': {'name': 'main', 'base_file': 'puncover.c', 'file': '/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c', 'address': '00000550', 'line': 25, 'size': 52, 'type': 'function'}})

    def test_parses_variable_line_from_initialized_data_section(self):
        c = Collector()
        line = "00000968 000000c8 D foo	/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c:15"
        self.assertTrue(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {'00000968': {'name': 'foo', 'base_file': 'puncover.c', 'file': '/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c', 'address': '00000968', 'line': 15, 'size': 200, 'type': 'variable'}})

    def test_parses_variable_line_from_uninitialized_data_section(self):
        c = Collector()
        line = "00000a38 00000008 b some_double_value	/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c:17"
        self.assertTrue(c.parse_size_line(line))
        print c.symbols
        self.assertDictEqual(c.symbols, {'00000a38': {'name': 'some_double_value', 'base_file': 'puncover.c', 'file': '/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c', 'address': '00000a38', 'line': 17, 'size': 8, 'type': 'variable'}})

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

    def test_parses_assembly2(self):
        assembly = """
00000098 <pbl_table_addr.constprop.0>:
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

    def test_parses_assembly_and_ignores_c(self):
        assembly = """
00000098 <pbl_table_addr>:
/path/to.c:8
pbl_table_addr():
  98:	a8a8a8a8 	.word	0xa8a8a8a8
"""
        c = Collector()
        self.assertEqual(1, c.parse_assembly_text(assembly))
        self.assertTrue(c.symbols.has_key("00000098"))
        self.assertEqual(c.symbols["00000098"]["name"], "pbl_table_addr")
        self.assertEqual(len(c.symbols["00000098"]["asm"]), 2)
        self.assertEqual(c.symbols["00000098"]["asm"][0], "pbl_table_addr():")


    def test_enhances_assembly(self):
        assembly = """
00000098 <pbl_table_addr>:
pbl_table_addr():
 568:	f7ff ffca 	bl	98
"""
        c = Collector()
        self.assertEqual(1, c.parse_assembly_text(assembly))
        self.assertTrue(c.symbols.has_key("00000098"))
        self.assertEqual(c.symbols["00000098"]["name"], "pbl_table_addr")
        self.assertEqual(c.symbols["00000098"]["asm"][1], " 568:\tf7ff ffca \tbl\t98")

        c.enhance_assembly()
        self.assertEqual(c.symbols["00000098"]["asm"][1], " 568:\tf7ff ffca \tbl\t98 <pbl_table_addr>")

    def test_enhances_caller(self):
        assembly = """
00000098 <pbl_table_addr>:
        8e4:	f000 f824 	bl	930 <app_log>

00000930 <app_log>:
$t():
        """
        c = Collector()
        self.assertEqual(2, c.parse_assembly_text(assembly))
        self.assertTrue(c.symbols.has_key("00000098"))
        self.assertTrue(c.symbols.has_key("00000930"))

        pbl_table_addr = c.symbols["00000098"]
        app_log = c.symbols["00000930"]

        self.assertFalse(pbl_table_addr.has_key("callers"))
        self.assertFalse(pbl_table_addr.has_key("callees"))
        self.assertFalse(app_log.has_key("callers"))
        self.assertFalse(app_log.has_key("callees"))

        c.enhance_call_tree()

        self.assertEqual(pbl_table_addr["callers"], [])
        self.assertEqual(pbl_table_addr["callees"], [app_log])
        self.assertEqual(app_log["callers"], [pbl_table_addr])
        self.assertEqual(app_log["callees"], [])


    def test_enhance_call_tree_from_assembly_line(self):
        c = Collector()
        f1 = "f1"
        f2 = {collector.ADDRESS: "00000088"}
        f3 = {collector.ADDRESS: "00000930"}
        c.symbols = {f2[collector.ADDRESS]: f2, f3[collector.ADDRESS]: f3}

        with patch.object(c, "add_function_call") as m:
            c.enhance_call_tree_from_assembly_line(f1, " 89e:	e9d3 0100 	ldrd	r0, r1, [r3]")
            self.assertFalse(m.called)
        with patch.object(c, "add_function_call") as m:
            c.enhance_call_tree_from_assembly_line(f1, "934:	f7ff bba8 	b.w	88 <jump_to_pbl_function>")
            m.assert_called_with(f1,f2)
        with patch.object(c, "add_function_call") as m:
            c.enhance_call_tree_from_assembly_line(f1, "8e4:	f000 f824 	bl	930 <app_log>")
            m.assert_called_with(f1,f3)

        with patch.object(c, "add_function_call") as m:
            c.enhance_call_tree_from_assembly_line(f1, "6c6:	d202      	bcs.n	88 <__aeabi_ddiv+0x6e>")
            m.assert_called_with(f1,f2)

        with patch.object(c, "add_function_call") as m:
            c.enhance_call_tree_from_assembly_line(f1, " 805bbac:	2471 0805 b64b 0804 b3c9 0804 b459 0804     q$..K.......Y...")
            self.assertFalse(m.called)


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

    def test_count_bytes(self):
        c = Collector()
        self.assertEqual(0, c.count_assembly_code_bytes("dynamic_stack2():"))
        self.assertEqual(2, c.count_assembly_code_bytes(" 88e:	4668      	mov	r0, sp"))
        self.assertEqual(4, c.count_assembly_code_bytes(" 88a:	ebad 0d03 	sub.w	sp, sp, r3"))
        self.assertEqual(4, c.count_assembly_code_bytes("878:	000001ba 	.word	0x000001ba"))

    def test_enhance_function_size_from_assembly(self):
        c = Collector()
        c.symbols = { "0000009c" : {
            collector.ADDRESS: "0000009c",
            collector.ASM: """
$t():
  9c:	f081 4100 	eor.w	r1, r1, #2147483648	; 0x80000000
  a0:	e002      	b.n	a8 <__adddf3>
  a2:	bf00      	nop
            """.split("\n")
        }}

        s = c.symbol_by_addr("9c")
        self.assertFalse(s.has_key(collector.SIZE))
        c.enhance_function_size_from_assembly()
        self.assertEqual(8, s[collector.SIZE])

    def test_enhance_sibling_symbols(self):
        c = Collector()
        aeabi_drsub = {
            collector.ADDRESS: "0000009c",
            collector.SIZE: 8,
            collector.TYPE: collector.TYPE_FUNCTION,
        }
        aeabi_dsub = {
            collector.ADDRESS: "000000a4",
            collector.SIZE: 4,
            collector.TYPE: collector.TYPE_FUNCTION,
        }
        adddf3 = {
            collector.ADDRESS: "000000a8",
            collector.SIZE: 123,
            collector.TYPE: collector.TYPE_FUNCTION,
        }

        c.symbols = {f[collector.ADDRESS]: f for f in [aeabi_drsub, aeabi_dsub, adddf3]}
        c.enhance_sibling_symbols()

        self.assertFalse(aeabi_drsub.has_key(collector.PREV_FUNCTION))
        self.assertEqual(aeabi_dsub, aeabi_drsub.get(collector.NEXT_FUNCTION))

        self.assertEqual(aeabi_drsub, aeabi_dsub.get(collector.PREV_FUNCTION))
        self.assertEqual(adddf3, aeabi_dsub.get(collector.NEXT_FUNCTION))

        self.assertEqual(aeabi_dsub, adddf3.get(collector.PREV_FUNCTION))
        self.assertFalse(adddf3.has_key(collector.NEXT_FUNCTION))


