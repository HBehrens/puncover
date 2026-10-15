import unittest

from puncover.gcc_vcg_parser import VCG_Edge, VCG_Graph, VCG_Label, VCG_Node, VCG_Parser


class Test_VCG_Parser(unittest.TestCase):
    def test_parse_empty_vcg_label(self):
        vcgp = VCG_Parser()
        test_label = ""
        ref = VCG_Label()

        test = vcgp.parse_vcg_label_attributes(test_label)
        self.assertEqual(ref, test, "test empty vcg label")

    def test_parse_vcg_label_indirect_call(self):
        vcgp = VCG_Parser()
        test_label = "Indirect Call Placeholder"
        ref = VCG_Label(
            function_name="Indirect Call Placeholder",
        )

        test = vcgp.parse_vcg_label_attributes(test_label)
        self.assertEqual(ref, test, "test vcg label - indirect call node parse matches")

    def test_parse_vcg_label_stack_and_da(self):
        # TODO add tests with dynamic allocation parsing, what can we us it for :?...
        vcgp = VCG_Parser()
        test_label = (
            "led_off_dt\\n/zephyr/drivers/led.h:432:19\\n15 bytes (static)\\n0 dynamic objects"
        )
        ref = VCG_Label(
            file_name="/zephyr/drivers/led.h",
            function_name="led_off_dt",
            line=432,
            column=19,
            stack_size=15,
            stack_qualifier="static",
        )

        test = vcgp.parse_vcg_label_attributes(test_label)
        self.assertEqual(ref, test, "test vcg label with stack use marker parse matches")

    def test_parse_node_indirect_call(self):
        vcgp = VCG_Parser()
        test_node = 'title: "__indirect_call" label: "Indirect Call Placeholder" shape : ellipse'
        ref = VCG_Node(
            title="__indirect_call",
            label=VCG_Label(
                function_name="Indirect Call Placeholder",
            ),
        )
        test = vcgp.parse_node(test_node)
        self.assertEqual(ref, test, "test vcg indirect call node parse matches")

    def test_parse_node_with_stackuse_marker(self):
        vcgp = VCG_Parser()
        test_node = 'title: "/zephyr/drivers/led.c:led_off_dt" label: "led_off_dt\\n/zephyr/include/drivers/led.h:432:19\\n15 bytes (static)\\n0 dynamic objects"'
        ref = VCG_Node(
            title="/zephyr/drivers/led.c:led_off_dt",
            label=VCG_Label(
                file_name="/zephyr/include/drivers/led.h",
                function_name="led_off_dt",
                line=432,
                column=19,
                stack_size=15,
                stack_qualifier="static",
            ),
        )
        test = vcgp.parse_node(test_node)
        self.assertEqual(ref, test, "test vcg node with stack use marker parse matches")

    def test_parse_edge(self):
        vcgp = VCG_Parser()
        test_edge = 'sourcename: "/app/src/led.c:led_state_normal_run" targetname: "smf_set_state" label: "/app/src/led.c:219:3"'
        ref = VCG_Edge(
            sourcename="/app/src/led.c:led_state_normal_run",
            targetname="smf_set_state",
            label="/app/src/led.c:219:3",
        )
        test = vcgp.parse_edge(test_edge)
        self.assertEqual(ref, test, "test vcg edge parse matches")

    def test_parse_graph_minimal(self):
        vcgp = VCG_Parser()
        test_graph = """graph: { title: "callgraph"
node: { title: "n0" label: "led_off_dt\\n/zephyr/drivers/led.h:432:19\\n15 bytes (static)\\n0 dynamic objects" shape: box }
node: { title: "n1" label: "helper" }
edge: { sourcename: "n0" targetname: "n1" label: "/app/src/led.c:219:3" }
}
        """

        ref = VCG_Graph(
            title="callgraph",
            nodes=[
                VCG_Node(
                    title="n0",
                    label=VCG_Label(
                        file_name="/zephyr/drivers/led.h",
                        function_name="led_off_dt",
                        line=432,
                        column=19,
                        stack_size=15,
                        stack_qualifier="static",
                    ),
                ),
                VCG_Node(
                    title="n1",
                    label=VCG_Label(
                        function_name="helper",
                    ),
                ),
            ],
            edges=[
                VCG_Edge(
                    sourcename="n0",
                    targetname="n1",
                    label="/app/src/led.c:219:3",
                )
            ],
        )
        test = vcgp.parse_vcg_graph(test_graph)
        self.assertEqual(test, ref, "test minimal vcg graph parse matches")
