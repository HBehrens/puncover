import unittest

from mock import patch

from puncover.gcc_vcg_parser import VCG_Parser, VCGLabel, VCGNode


class Test_VCG_Parser(unittest.TestCase):

    def test_parse_empty_vcg_label(self):
        vcgp = VCG_Parser()
        test_label =""
        ref = VCGLabel()

        test = vcgp.parse_vcg_label_attributes(test_label)
        self.assertEqual(ref, test, "test empty vcg label")


    def test_parse_vcg_label_indirect_call(self):
        vcgp = VCG_Parser()
        test_label ="Indirect Call Placeholder"
        ref = VCGLabel(
            function_name="Indirect Call Placeholder",
        )

        test = vcgp.parse_vcg_label_attributes(test_label)
        self.assertEqual(ref, test, "test vcg label - indirect call node parse matches")

    def test_parse_vcg_label_stack_and_da(self):
        # TODO add tests with dynamic allocation parsing, what can we us it for :?...
        vcgp = VCG_Parser()
        test_label ="led_off_dt\n/zephyr/drivers/led.h:432:19\n15 bytes (static)\n0 dynamic objects"
        ref = VCGLabel(
            file_name="/zephyr/drivers/led.h",
            function_name="led_off_dt",
            line=432,
            column=19,
            stack_size=15,
            stack_qualifier="static"
        )

        test = vcgp.parse_vcg_label_attributes(test_label)
        self.assertEqual(ref, test, "test vcg label with stack use marker parse matches")

    def test_parse_node_indirect_call(self):
        vcgp = VCG_Parser()
        test_node = 'title: "__indirect_call" label: "Indirect Call Placeholder" shape : ellipse'
        ref = VCGNode(
            title="__indirect_call",
            label=VCGLabel(
                function_name="Indirect Call Placeholder",
            )
        )
        test = vcgp.parse_node(test_node)
        self.assertEqual(ref, test, "test vcg indirect call node parse matches")


    def test_parse_node_with_stackuse_marker(self):
        vcgp = VCG_Parser()
        test_node = 'title: "/zephyr/drivers/led.c:led_off_dt" label: "led_off_dt\n/zephyr/include/drivers/led.h:432:19\n15 bytes (static)\n0 dynamic objects"'
        ref = VCGNode(
            title="/zephyr/drivers/led.c:led_off_dt",
            label=VCGLabel(
                file_name="/zephyr/include/drivers/led.h",
                function_name="led_off_dt",
                line=432,
                column=19,
                stack_size=15,
                stack_qualifier="static"
            )
        )
        test = vcgp.parse_node(test_node)
        self.assertEqual(ref, test, "test vcg node with stack use marker parse matches")
