import unittest

from puncover import collector
from puncover.backtrace_helper import BacktraceHelper


class TestBacktraceHelper(unittest.TestCase):
    class FakeCollector:
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
        r = BacktraceHelper(
            TestBacktraceHelper.FakeCollector([
                "codepoint_get_horizontal_advance",
                "text_walk_lines",
            ])
        )
        actual = r.derive_function_symbols("""
    fontinfo=0x200010ec <s_system_fonts_info_table+200>) 16 at ../src/fw/applib/graphics/text_resources.c:347
#4  0x08012220 in codepoint_get_horizontal_advance () 16
#5  0x08012602 in walk_line () 112
#6  0x080128d6 in text_walk_lines.constprop.8 () (inlined)
        """)

        self.assertEqual(
            ["codepoint_get_horizontal_advance", "text_walk_lines"],
            [f[collector.NAME] for f in actual],
        )

    def test_transform_known_symbols(self):
        r = BacktraceHelper(
            TestBacktraceHelper.FakeCollector([
                "a",
                "c",
                "d",
            ])
        )

        def f(symbol):
            return symbol[collector.NAME] + symbol[collector.NAME]

        actual = r.transform_known_symbols("0 1 a b c d e f 0 2", f)
        self.assertEqual("0 1 aa b cc dd e f 0 2", actual)


class TestBacktraceHelperTreeSizes(unittest.TestCase):
    def setUp(self):
        self.cc = collector.Collector(None)
        self.a = self.cc.add_symbol("a", "a", type=collector.TYPE_FUNCTION, stack_size=1)
        self.b = self.cc.add_symbol("b", "b", type=collector.TYPE_FUNCTION, stack_size=10)
        self.c = self.cc.add_symbol("c", "c", type=collector.TYPE_FUNCTION, stack_size=100)
        self.d = self.cc.add_symbol("d", "d", type=collector.TYPE_FUNCTION, stack_size=1000)
        self.e = self.cc.add_symbol("e", "e", type=collector.TYPE_FUNCTION, stack_size=10000)
        self.f = self.cc.add_symbol("f", "f", type=collector.TYPE_FUNCTION)
        self.cc.enhance_call_tree()
        self.cc.add_function_call(self.a, self.b)
        self.cc.add_function_call(self.a, self.c)
        self.cc.add_function_call(self.b, self.a)
        self.cc.add_function_call(self.c, self.b)
        self.cc.add_function_call(self.c, self.d)
        self.cc.add_function_call(self.d, self.e)
        self.cc.add_function_call(self.d, self.f)
        self.h = BacktraceHelper(self.cc)

    def test_leaf_with_stack(self):
        self.assertEqual((10000, [self.e]), self.h.deepest_callee_tree(self.e))
        self.assertIn(collector.DEEPEST_CALLEE_TREE, self.e)

    def test_leaf_without_stack(self):
        self.assertEqual((0, [self.f]), self.h.deepest_callee_tree(self.f))
        self.assertIn(collector.DEEPEST_CALLEE_TREE, self.f)

    def test_cached_value(self):
        self.f[collector.DEEPEST_CALLEE_TREE] = "cached"
        self.assertEqual("cached", self.h.deepest_callee_tree(self.f))

    def test_non_leaf(self):
        self.assertEqual((11000, [self.d, self.e]), self.h.deepest_callee_tree(self.d))
        self.assertIn(collector.DEEPEST_CALLEE_TREE, self.f)
        self.assertIn(collector.DEEPEST_CALLEE_TREE, self.e)
        self.assertIn(collector.DEEPEST_CALLEE_TREE, self.d)

    def test_cycle_2(self):
        self.a[collector.CALLEES].remove(self.c)

        expected = (11, [self.a, self.b])
        actual = self.h.deepest_callee_tree(self.a)
        self.assertEqual(expected, actual)

        # b -> a -> (b dropped as a back-edge): the longest simple path is b + a.
        # The previous implementation returned the cache-poisoned (10, [b]) here,
        # because computing a first cached b without a on the path.
        expected = (11, [self.b, self.a])
        actual = self.h.deepest_callee_tree(self.b)
        self.assertEqual(expected, actual)

    def test_cycle_3(self):
        self.c[collector.CALLEES].remove(self.d)
        # Longest simple path through the a<->b / a->c->b cycle is a+b+c = 111
        # for every entry node; previously b and c returned cache-poisoned 10/110.
        self.assertEqual(111, self.h.deepest_callee_tree(self.a)[0])
        self.assertEqual(111, self.h.deepest_callee_tree(self.b)[0])
        self.assertEqual(111, self.h.deepest_callee_tree(self.c)[0])

    def test_cycle_order_independent(self):
        # Same graph as test_cycle_3, but compute b FIRST -- the order that used
        # to poison the shared cache. Every node must still get the correct value.
        self.c[collector.CALLEES].remove(self.d)
        self.assertEqual(111, self.h.deepest_callee_tree(self.b)[0])
        self.assertEqual(111, self.h.deepest_callee_tree(self.c)[0])
        self.assertEqual(111, self.h.deepest_callee_tree(self.a)[0])

    def test_caller(self):
        self.d[collector.CALLERS] = []
        self.assertEqual(1000, self.h.deepest_caller_tree(self.f)[0])
        self.assertEqual(11000, self.h.deepest_caller_tree(self.e)[0])

    def test_caller_cycle(self):
        self.assertEqual(1111, self.h.deepest_caller_tree(self.f)[0])
        self.assertEqual(11111, self.h.deepest_caller_tree(self.e)[0])

    def test_recursion_flag_mutual(self):
        cc = collector.Collector(None)
        x = cc.add_symbol("x", "10", type=collector.TYPE_FUNCTION, stack_size=1)
        y = cc.add_symbol("y", "20", type=collector.TYPE_FUNCTION, stack_size=1)
        z = cc.add_symbol("z", "30", type=collector.TYPE_FUNCTION, stack_size=1)
        cc.enhance_call_tree()
        cc.add_function_call(x, y)
        cc.add_function_call(y, x)  # x <-> y mutual recursion; z is independent
        h = BacktraceHelper(cc)
        for fn in (x, y, z):
            h.deepest_callee_tree(fn)
            h.deepest_caller_tree(fn)
        h.annotate_call_tree_flags()
        self.assertTrue(x.get(collector.RECURSION_IN_CALL_TREE))
        self.assertTrue(y.get(collector.RECURSION_IN_CALL_TREE))
        self.assertFalse(z.get(collector.RECURSION_IN_CALL_TREE))

    def test_recursion_flag_direct(self):
        cc = collector.Collector(None)
        r = cc.add_symbol("r", "40", type=collector.TYPE_FUNCTION, stack_size=1)
        s = cc.add_symbol("s", "50", type=collector.TYPE_FUNCTION, stack_size=1)
        cc.enhance_call_tree()
        cc.add_function_call(r, r)  # direct self-recursion
        cc.add_function_call(s, r)  # s -> r reaches the recursive r
        h = BacktraceHelper(cc)
        for fn in (r, s):
            h.deepest_callee_tree(fn)
            h.deepest_caller_tree(fn)
        h.annotate_call_tree_flags()
        self.assertTrue(r.get(collector.RECURSION_IN_CALL_TREE))
        self.assertTrue(s.get(collector.RECURSION_IN_CALL_TREE))

    def test_warning_flags_are_transitive(self):
        # a -> b -> d, where d (deep in a's tree) performs an indirect call.
        # The flag must reach a, not only d's direct parent b (F7).
        cc = collector.Collector(None)
        a = cc.add_symbol("a", "10", type=collector.TYPE_FUNCTION, stack_size=1)
        b = cc.add_symbol("b", "20", type=collector.TYPE_FUNCTION, stack_size=1)
        d = cc.add_symbol("d", "30", type=collector.TYPE_FUNCTION, stack_size=1)
        d[collector.PERFORMS_INDIRECT_CALL] = True
        cc.enhance_call_tree()
        cc.add_function_call(a, b)
        cc.add_function_call(b, d)
        h = BacktraceHelper(cc)
        h.annotate_call_tree_flags()
        self.assertEqual(1, a.get(collector.UNRESOLVED_CALLS_IN_CALL_TREE))
        self.assertEqual(1, b.get(collector.UNRESOLVED_CALLS_IN_CALL_TREE))
