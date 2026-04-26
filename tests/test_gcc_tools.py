import unittest

from mock import patch

from puncover.gcc_tools import GCCTools


class TestGCCTools(unittest.TestCase):
    def test_arm_indirect_call_pattern(self):
        t = GCCTools("arm-none-eabi-")
        p = t.indirect_call_pattern
        self.assertIsNotNone(p)

        # matches indirect call via register
        self.assertIsNotNone(p.match("805d83c:\t47b0     \tblx\tr6"))
        # case-insensitive
        self.assertIsNotNone(p.match("805d83c:\t47b0     \tBLX\tr6"))
        # direct call with label suffix should NOT match
        self.assertIsNone(p.match("8e4:\tf000 f824\tblx\t930 <app_log>"))

    def test_riscv_indirect_call_pattern_is_none(self):
        t = GCCTools("riscv32-unknown-elf-")
        self.assertIsNone(t.indirect_call_pattern)

    def test_chunks_and_rstrip(self):
        t = GCCTools("somePath")
        with patch.object(t, "gcc_tool_lines") as f:
            f.side_effect = lambda cmd, symbols: [" -%s- " % s for s in symbols]
            actual = t.get_unmangled_names(["a", "b", "c", "d", "e"], 2)
            self.assertEqual(
                {"a": " -a-", "b": " -b-", "c": " -c-", "d": " -d-", "e": " -e-"}, actual
            )
