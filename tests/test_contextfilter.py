import unittest
from puncover.renderers import traverse_filter_wrapper


class TestBacktraceHelper(unittest.TestCase):

    def test_traverse_filter_wrapper_single_none(self):
        actual = traverse_filter_wrapper({}, lambda s: None)
        self.assertIsNone(actual)

    def test_traverse_filter_wrapper_list_of_none(self):
        actual = traverse_filter_wrapper([{}, {}], lambda s: None)
        self.assertIsNone(actual)

    def test_traverse_filter_wrapper_list_ignores_none_first(self):
        actual = traverse_filter_wrapper([{}, {"v": 1}], lambda s: s.get("v", None))
        self.assertEqual(actual, 1)

    def test_traverse_filter_wrapper_list_ignores_none_mid(self):
        actual = traverse_filter_wrapper([{"v": 1}, {}, {"v": 3}], lambda s: s.get("v", None))
        self.assertEqual(actual, 4)

    def test_traverse_filter_wrapper_list_ignores_none_last(self):
        actual = traverse_filter_wrapper([{"v": 1}, {}], lambda s: s.get("v", None))
        self.assertEqual(actual, 1)
