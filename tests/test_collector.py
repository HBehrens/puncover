import unittest
from puncover.collector import Collector, left_strip_from_list
from mock import patch
from puncover import collector


class TestCollector(unittest.TestCase):

    def setUp(self):
        pass

    def test_left_strip_from_list(self):
        self.assertEqual(left_strip_from_list(["  a", "   b"]), ["a", " b"])

    def test_parses_function_line(self):
        c = Collector(None)
        line = "00000550 00000034 T main	/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c:25"
        self.assertTrue(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {0x00000550: {'name': 'main', 'base_file': 'puncover.c', 'path': '/Users/behrens/Documents/projects/pebble/puncover/puncover/build/../src/puncover.c', 'address': '00000550', 'line': 25, 'size': 52, 'type': 'function'}})

    def test_parses_variable_line_from_initialized_data_section(self):
        c = Collector(None)
        line = "00000968 000000c8 D foo	/Users/behrens/Documents/projects/pebble/puncover/pebble/build/puncover.c:15"
        self.assertTrue(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {0x00000968: {'name': 'foo', 'base_file': 'puncover.c', 'path': '/Users/behrens/Documents/projects/pebble/puncover/pebble/build/puncover.c', 'address': '00000968', 'line': 15, 'size': 200, 'type': 'variable'}})

    def test_parses_variable_line_from_uninitialized_data_section(self):
        c = Collector(None)
        line = "00000a38 00000008 b some_double_value	/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c:17"
        self.assertTrue(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {0x00000a38: {'name': 'some_double_value', 'base_file': 'puncover.c', 'path': '/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c', 'address': '00000a38', 'line': 17, 'size': 8, 'type': 'variable'}})

    def test_ignores_incomplete_size_line_1(self):
        c = Collector(None)
        line = "0000059c D __dso_handle"
        self.assertFalse(c.parse_size_line(line))
        self.assertDictEqual(c.symbols, {})

    def test_ignores_incomplete_size_line_2(self):
        c = Collector(None)
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
        c = Collector(None)
        self.assertEqual(2, c.parse_assembly_text(assembly))
        self.assertTrue(0x0000009c in c.symbols)
        self.assertEqual(c.symbols[0x0000009c]["name"], "__aeabi_dmul")
        self.assertTrue(0x00000098 in c.symbols)
        self.assertEqual(c.symbols[0x00000098]["name"], "pbl_table_addr")

    def test_parses_assembly2(self):
        assembly = """
00000098 <pbl_table_addr.constprop.0>:
pbl_table_addr():
  98:	a8a8a8a8 	.word	0xa8a8a8a8

0000009c <__aeabi_dmul>:
__aeabi_dmul():
  9c:	b570      	push	{r4, r5, r6, lr}
"""
        c = Collector(None)
        self.assertEqual(2, c.parse_assembly_text(assembly))
        self.assertTrue(0x0000009c in c.symbols)
        self.assertEqual(c.symbols[0x0000009c]["name"], "__aeabi_dmul")
        self.assertTrue(0x00000098 in c.symbols)
        self.assertEqual(c.symbols[0x00000098]["name"], "pbl_table_addr")

    def test_parses_assembly_and_ignores_c(self):
        assembly = """
00000098 <pbl_table_addr>:
/path/to.c:8
pbl_table_addr():
  98:	a8a8a8a8 	.word	0xa8a8a8a8
"""
        c = Collector(None)
        self.assertEqual(1, c.parse_assembly_text(assembly))
        self.assertTrue(0x00000098 in c.symbols)
        self.assertEqual(c.symbols[0x00000098]["name"], "pbl_table_addr")
        self.assertEqual(len(c.symbols[0x00000098]["asm"]), 2)
        self.assertEqual(c.symbols[0x00000098]["asm"][0], "pbl_table_addr():")

    def test_parses_assembly_and_stops_after_function(self):
        assembly = """
000034fc <window_raw_click_subscribe>:
$t():
    34fc:	b40f      	push	{r0, r1, r2, r3}
    34fe:	4901      	ldr	r1, [pc, #4]	; (3504 <window_raw_click_subscribe+0x8>)
    3500:	f7fc bdc2 	b.w	88 <jump_to_pbl_function>
$d():
    3504:	000004c4 	.word	0x000004c4
    3508:	00040000 	.word	0x00040000
    350c:	000b008d 	.word	0x000b008d

00003510 <.LC1>:
.LC1():
    3510:	69727073 	.word	0x69727073
    3514:	42736574 	.word	0x42736574
    3518:	31647269 	.word	0x31647269
    351c:	0036      	.short	0x0036

"""

        c = Collector(None)
        self.assertEqual(2, c.parse_assembly_text(assembly))
        self.assertTrue(0x000034fc in c.symbols)
        self.assertEqual(c.symbols[0x000034fc]["name"], "window_raw_click_subscribe")
        # print "\n".join(c.symbols["000034fc"]["asm"])
        self.assertEqual(len(c.symbols[0x000034fc]["asm"]), 8)


    def test_enhances_assembly(self):
        assembly = """
00000098 <pbl_table_addr>:
pbl_table_addr():
 568:	f7ff ffca 	bl	98
"""
        c = Collector(None)
        self.assertEqual(1, c.parse_assembly_text(assembly))
        self.assertTrue(0x00000098 in c.symbols)
        self.assertEqual(c.symbols[0x00000098]["name"], "pbl_table_addr")
        self.assertEqual(c.symbols[0x00000098]["asm"][1], " 568:\tf7ff ffca \tbl\t98")

        c.enhance_assembly()
        self.assertEqual(c.symbols[0x00000098]["asm"][1], " 568:\tf7ff ffca \tbl\t98 <pbl_table_addr>")

    def test_enhances_caller(self):
        assembly = """
00000098 <pbl_table_addr>:
        8e4:	f000 f824 	bl	930 <app_log>

00000930 <app_log>:
$t():
        """
        c = Collector(None)
        self.assertEqual(2, c.parse_assembly_text(assembly))
        self.assertTrue(0x00000098 in c.symbols)
        self.assertTrue(0x00000930 in c.symbols)

        pbl_table_addr = c.symbols[0x00000098]
        app_log = c.symbols[0x00000930]

        self.assertFalse("callers" in pbl_table_addr)
        self.assertFalse("callees" in pbl_table_addr)
        self.assertFalse("callers" in app_log)
        self.assertFalse("callees" in app_log)

        c.enhance_call_tree()

        self.assertEqual(pbl_table_addr["callers"], [])
        self.assertEqual(pbl_table_addr["callees"], [app_log])
        self.assertEqual(app_log["callers"], [pbl_table_addr])
        self.assertEqual(app_log["callees"], [])


    def test_enhance_call_tree_from_assembly_line(self):
        c = Collector(None)
        f1 = "f1"
        f2 = {collector.ADDRESS: "00000088"}
        f3 = {collector.ADDRESS: "00000930"}
        c.symbols = {int(f2[collector.ADDRESS], 16): f2, int(f3[collector.ADDRESS], 16): f3}

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
        c = Collector(None)
        c.symbols = {"123": {
            "base_file": "puncover.c",
            "line": 14,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))
        self.assertEqual(16, c.symbols["123"]["stack_size"])
        self.assertEqual("dynamic,bounded", c.symbols["123"]["stack_qualifiers"])

    def test_stack_usage_line2(self):
        line = "puncover.c:8:43:dynamic_stack2	16	dynamic"
        c = Collector(None)
        c.symbols = {"123": {
            "base_file": "puncover.c",
            "line": 8,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))

    def test_stack_usage_line_header(self):
        line = "ILI9341_t3.h:312:15:void ILI9341_t3::updateDisplayClip()	16	static"
        c = Collector(None)
        c.symbols = {"123": {
            "base_file": "ILI9341_t3.h",
            "line": 312,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))

    def test_stack_usage_line_cpp_correct_line(self):
        line = "Print.cpp:34:8:virtual size_t Print::write(const uint8_t*, size_t)	24	static"
        c = Collector(None)
        c.symbols = {"123": {
            "base_file": "Print.cpp",
            "line": 34,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))
        self.assertEqual(24, c.symbols["123"]["stack_size"])
        self.assertEqual("static", c.symbols["123"]["stack_qualifiers"])

    def test_stack_usage_line_cpp_incorrect_line(self):
        line = "Print.cpp:34:8:virtual size_t Print::write(const uint8_t*, size_t)	24	static"
        c = Collector(None)
        c.symbols = {"123": {
            "base_file": "Print.cpp",
            "display_name": "virtual size_t Print::write(const uint8_t*, size_t)",
            "line": 35,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))
        self.assertEqual(24, c.symbols["123"]["stack_size"])
        self.assertEqual("static", c.symbols["123"]["stack_qualifiers"])

    def test_stack_usage_line_cpp_constructor(self):
        line = "WString.cpp:82:1:String::String(unsigned int, unsigned char)	32	static"
        c = Collector(None)
        c.symbols = {"123": {
            "base_file": "WString.cpp",
            "line": 82,
        }}
        self.assertTrue(c.parse_stack_usage_line(line))

    def test_display_names_match(self):
        c = Collector(None)

        def f(a, b):
            return c.display_names_match(a, b)

        self.assertFalse(f(None, "func_a"))
        self.assertFalse(f("func_a", None))
        self.assertFalse(f("func_a", "func_b"))
        self.assertTrue(f("func_a", "func_a"))

        self.assertTrue(f("size_t Print::println()", "Print::println()"))
        self.assertFalse(f("size_t Print::println(int)", "Print::println(char)"))
        self.assertTrue(f("virtual size_t Print::write(const uint8_t*, size_t)", "Print::write(unsigned char const*, unsigned int)"))
        self.assertTrue(f("static void SPIClass::begin()", "SPIClass::begin()"))
        self.assertTrue(f("static uint8_t i2c_t3::setRate_(i2cStruct*, uint32_t, i2c_rate)", "i2c_t3::setRate_(i2cStruct*, unsigned long, i2c_rate)"))
        self.assertTrue(f("void ILI9341_t3::drawFontBits(bool, uint32_t, uint32_t, int32_t, int32_t, uint32_t)", "ILI9341_t3::drawFontBits(bool, unsigned long, unsigned long, long, long, unsigned long)"))
        self.assertTrue(f("imu::Vector<3u> Adafruit_BNO055::getVector(Adafruit_BNO055::adafruit_vector_type_t)", "Adafruit_BNO055::getVector(Adafruit_BNO055::adafruit_vector_type_t)"))
        self.assertTrue(f("uint8_t Adafruit_BMP280::read8(byte)", "Adafruit_BMP280::read8(unsigned char)"))
        self.assertTrue(f("NMEAReaderTask::NMEAReaderTask(HardwareSerial&)", "NMEAReaderTask::NMEAReaderTask(HardwareSerial&)"))
        self.assertTrue(f("virtual Page::~Page()", "Page::~Page()"))

        self.assertFalse(f("void tN2kMsg::SendInActisenseFormat(N2kStream*) const", "tN2kMsg::Print(Stream*, bool) const"))
        self.assertTrue(f("virtual bool BasePage::processEvent(const Event&)", "BasePage::processEvent(Event const&)"))
        self.assertTrue(f("String::String(unsigned int, unsigned char)", "String::String(unsigned int, unsigned char)"))
        self.assertTrue(f("bool SDCardTask::isLogging() const", "SDCardTask::isLogging() const"))


    def test_count_bytes(self):
        c = Collector(None)
        self.assertEqual(0, c.count_assembly_code_bytes("dynamic_stack2():"))
        self.assertEqual(2, c.count_assembly_code_bytes(" 88e:	4668      	mov	r0, sp"))
        self.assertEqual(4, c.count_assembly_code_bytes(" 88a:	ebad 0d03 	sub.w	sp, sp, r3"))
        self.assertEqual(4, c.count_assembly_code_bytes("878:	000001ba 	.word	0x000001ba"))

    def test_enhance_function_size_from_assembly(self):
        c = Collector(None)
        c.symbols = { int("0000009c", 16) : {
            collector.ADDRESS: "0000009c",
            collector.ASM: """
$t():
  9c:	f081 4100 	eor.w	r1, r1, #2147483648	; 0x80000000
  a0:	e002      	b.n	a8 <__adddf3>
  a2:	bf00      	nop
            """.split("\n")
        }}

        s = c.symbol_by_addr("9c")
        self.assertFalse(collector.SIZE in s)
        c.enhance_function_size_from_assembly()
        self.assertEqual(8, s[collector.SIZE])

    def test_derive_filename_from_assembly(self):
        c = Collector(None)
        c.parse_assembly_text("""
000008a8 <uses_doubles2.constprop.0>:
uses_doubles2():
/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c:19
 8a8:	b508      	push	{r3, lr}
         """)
        s = c.symbol_by_addr("8a8")
        self.assertEqual("/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c", s[collector.PATH])
        self.assertEqual("puncover.c", s[collector.BASE_FILE])
        self.assertEqual(19, s[collector.LINE])


    def test_enhance_sibling_symbols(self):
        c = Collector(None)
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

        c.symbols = {int(f[collector.ADDRESS], 16): f for f in [aeabi_drsub, aeabi_dsub, adddf3]}
        c.enhance_sibling_symbols()

        self.assertFalse(collector.PREV_FUNCTION in aeabi_drsub)
        self.assertEqual(aeabi_dsub, aeabi_drsub.get(collector.NEXT_FUNCTION))

        self.assertEqual(aeabi_drsub, aeabi_dsub.get(collector.PREV_FUNCTION))
        self.assertEqual(adddf3, aeabi_dsub.get(collector.NEXT_FUNCTION))

        self.assertEqual(aeabi_dsub, adddf3.get(collector.PREV_FUNCTION))
        self.assertFalse(collector.NEXT_FUNCTION in adddf3)

    def test_derive_file_elements(self):
        c = Collector(None)
        s1 = {collector.PATH: "/Users/behrens/Documents/projects/pebble/puncover/pebble/build/../src/puncover.c"}
        s2 = {collector.PATH: "/Users/thomas/work/arm-eabi-toolchain/build/gcc-final/arm-none-eabi/thumb2/libgcc/../../../../../gcc-4.7-2012.09/libgcc/config/arm/ieee754-df.S"}
        s3 = {collector.PATH: "src/puncover.c"}
        c.symbols = {
            1: s1,
            2: s2,
            3: s3,
        }

        c.derive_folders()
        self.assertEqual("/Users/behrens/Documents/projects/pebble/puncover/pebble/src/puncover.c", s1[collector.PATH])
        self.assertIsNotNone(s1[collector.FILE])

        self.assertEqual("/Users/thomas/work/arm-eabi-toolchain/gcc-4.7-2012.09/libgcc/config/arm/ieee754-df.S", s2[collector.PATH])
        self.assertIsNotNone(s2[collector.FILE])

        self.assertEqual("src/puncover.c", s3[collector.PATH])
        self.assertIsNotNone(s3[collector.FILE])

    def test_derive_file_elements_for_unknown_files(self):
        c = Collector(None)
        s = c.add_symbol("some_symbol", "00a")
        self.assertEqual("some_symbol", s[collector.NAME])
        self.assertNotIn(collector.PATH, s)
        self.assertNotIn(collector.BASE_FILE, s)
        c.derive_folders()
        self.assertEqual("<unknown>/<unknown>", s[collector.PATH])
        self.assertEqual("<unknown>", s[collector.BASE_FILE])
        self.assertIn(collector.FILE, s)
        file = s[collector.FILE]
        self.assertEqual("<unknown>", file[collector.NAME])
        folder = file[collector.FOLDER]
        self.assertEqual("<unknown>", file[collector.NAME])



    def test_enhance_file_elements(self):
        c = Collector(None)
        aa_c = c.file_for_path("a/a/aa.c")
        ab_c = c.file_for_path("a/b/ab.c")
        b_c = c.file_for_path("b/b.c")
        baa_c = c.file_for_path("b/a/a/baa.c")

        a = c.folder_for_path("a")
        aa = c.folder_for_path("a/a")
        ab = c.folder_for_path("a/b")
        b = c.folder_for_path("b")
        ba = c.folder_for_path("b/a")
        baa = c.folder_for_path("b/a/a")

        self.assertEqual("a", a[collector.NAME])
        self.assertEqual("a", aa[collector.NAME])
        self.assertEqual("aa.c", aa_c[collector.NAME])
        self.assertEqual("b", ab[collector.NAME])
        self.assertEqual("ab.c", ab_c[collector.NAME])
        self.assertEqual("b", b[collector.NAME])
        self.assertEqual("b.c", b_c[collector.NAME])
        self.assertEqual("a", ba[collector.NAME])
        self.assertEqual("a", baa[collector.NAME])
        self.assertEqual("baa.c", baa_c[collector.NAME])

        c.enhance_file_elements()

        crf = list(c.collapsed_root_folders())
        self.assertListEqual([aa, ab, b], crf)

        self.assertEqual(a, aa[collector.ROOT])
        self.assertEqual(a, ab[collector.ROOT])
        self.assertEqual(b, ba[collector.ROOT])
        self.assertEqual(b, baa[collector.ROOT])

        self.assertListEqual([aa, ab], a[collector.SUB_FOLDERS])
        self.assertListEqual([], aa[collector.SUB_FOLDERS])
        self.assertListEqual([], ab[collector.SUB_FOLDERS])
        self.assertListEqual([ba], b[collector.SUB_FOLDERS])
        self.assertListEqual([baa], ba[collector.SUB_FOLDERS])
        self.assertListEqual([], baa[collector.SUB_FOLDERS])

        self.assertListEqual([], a[collector.FILES])
        self.assertListEqual([aa_c], aa[collector.FILES])
        self.assertListEqual([ab_c], ab[collector.FILES])
        self.assertListEqual([b_c], b[collector.FILES])
        self.assertListEqual([], ba[collector.FILES])
        self.assertListEqual([baa_c], baa[collector.FILES])

        self.assertEqual("a", a[collector.COLLAPSED_NAME])
        self.assertEqual("a/a", aa[collector.COLLAPSED_NAME])
        self.assertEqual("a/b", ab[collector.COLLAPSED_NAME])
        self.assertEqual("b", b[collector.COLLAPSED_NAME])
        self.assertEqual("a", ba[collector.COLLAPSED_NAME])
        self.assertEqual("a/a", baa[collector.COLLAPSED_NAME])

        self.assertListEqual([aa, ab], a[collector.COLLAPSED_SUB_FOLDERS])
        self.assertListEqual([], aa[collector.COLLAPSED_SUB_FOLDERS])
        self.assertListEqual([], ab[collector.COLLAPSED_SUB_FOLDERS])
        self.assertListEqual([baa], b[collector.COLLAPSED_SUB_FOLDERS])
        self.assertListEqual([baa], ba[collector.COLLAPSED_SUB_FOLDERS])
        self.assertListEqual([], baa[collector.COLLAPSED_SUB_FOLDERS])

