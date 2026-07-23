import json
import os
import tempfile
import unittest
from unittest.mock import patch

from puncover.collector import (
    CALLEES,
    CALLERS,
    TYPE,
    TYPE_FUNCTION,
    Collector,
)


def _make_collector_with_functions(*name_addr_pairs):
    """Return a Collector pre-populated with function symbols that have empty
    CALLEES/CALLERS lists (mimicking post-enhance_call_tree state)."""
    c = Collector(None)
    for name, addr in name_addr_pairs:
        sym = c.add_symbol(name, addr, type=TYPE_FUNCTION)
        sym[CALLEES] = []
        sym[CALLERS] = []
    c.build_symbol_name_index()
    return c


def _write_json(data):
    """Write *data* to a temp file and return its path (caller must delete)."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


class TestAddIndirectCalleesFromFile(unittest.TestCase):

    def test_adds_callee_edges_for_known_symbols(self):
        c = _make_collector_with_functions(
            ("caller_func", "0x1000"),
            ("callee_one",  "0x2000"),
            ("callee_two",  "0x3000"),
        )
        caller  = c.symbol("caller_func",  qualified=False)
        callee1 = c.symbol("callee_one",   qualified=False)
        callee2 = c.symbol("callee_two",   qualified=False)

        tmp = _write_json({
            "version": 1,
            "indirect_callees": [
                {"caller": "caller_func", "callees": ["callee_one", "callee_two"]}
            ],
        })
        try:
            c.add_indirect_callees_from_file(tmp)
        finally:
            os.unlink(tmp)

        self.assertIn(callee1, caller[CALLEES])
        self.assertIn(callee2, caller[CALLEES])
        self.assertIn(caller, callee1[CALLERS])
        self.assertIn(caller, callee2[CALLERS])

    def test_multiple_caller_entries(self):
        c = _make_collector_with_functions(
            ("dispatcher_a", "0x1000"),
            ("dispatcher_b", "0x1100"),
            ("handler_x",    "0x2000"),
            ("handler_y",    "0x2100"),
            ("handler_z",    "0x2200"),
        )
        tmp = _write_json({
            "version": 1,
            "indirect_callees": [
                {"caller": "dispatcher_a", "callees": ["handler_x", "handler_y"]},
                {"caller": "dispatcher_b", "callees": ["handler_z"]},
            ],
        })
        try:
            c.add_indirect_callees_from_file(tmp)
        finally:
            os.unlink(tmp)

        da = c.symbol("dispatcher_a", qualified=False)
        db = c.symbol("dispatcher_b", qualified=False)
        hx = c.symbol("handler_x",    qualified=False)
        hy = c.symbol("handler_y",    qualified=False)
        hz = c.symbol("handler_z",    qualified=False)

        self.assertIn(hx, da[CALLEES])
        self.assertIn(hy, da[CALLEES])
        self.assertIn(hz, db[CALLEES])
        self.assertNotIn(hz, da[CALLEES])

    def test_does_not_add_duplicate_edges(self):
        c = _make_collector_with_functions(
            ("caller_func", "0x1000"),
            ("callee_one",  "0x2000"),
        )
        caller  = c.symbol("caller_func", qualified=False)
        callee1 = c.symbol("callee_one",  qualified=False)

        data = {
            "version": 1,
            "indirect_callees": [
                {"caller": "caller_func", "callees": ["callee_one"]}
            ],
        }
        tmp = _write_json(data)
        try:
            c.add_indirect_callees_from_file(tmp)
            c.add_indirect_callees_from_file(tmp)  # call twice
        finally:
            os.unlink(tmp)

        self.assertEqual(caller[CALLEES].count(callee1), 1)
        self.assertEqual(callee1[CALLERS].count(caller), 1)

    def test_warns_on_unknown_caller(self):
        c = _make_collector_with_functions(
            ("callee_one", "0x2000"),
        )
        tmp = _write_json({
            "version": 1,
            "indirect_callees": [
                {"caller": "no_such_function", "callees": ["callee_one"]}
            ],
        })
        try:
            with patch("puncover.collector.warning") as mock_warn:
                c.add_indirect_callees_from_file(tmp)
                mock_warn.assert_called_once()
                self.assertIn("no_such_function", mock_warn.call_args[0][0])
        finally:
            os.unlink(tmp)

    def test_warns_on_unknown_callee(self):
        c = _make_collector_with_functions(
            ("caller_func", "0x1000"),
        )
        tmp = _write_json({
            "version": 1,
            "indirect_callees": [
                {"caller": "caller_func", "callees": ["no_such_callee"]}
            ],
        })
        try:
            with patch("puncover.collector.warning") as mock_warn:
                c.add_indirect_callees_from_file(tmp)
                mock_warn.assert_called_once()
                self.assertIn("no_such_callee", mock_warn.call_args[0][0])
        finally:
            os.unlink(tmp)

    def test_skips_entry_missing_caller_field(self):
        c = _make_collector_with_functions(
            ("callee_one", "0x2000"),
        )
        tmp = _write_json({
            "version": 1,
            "indirect_callees": [
                {"callees": ["callee_one"]}   # no "caller" key
            ],
        })
        try:
            with patch("puncover.collector.warning") as mock_warn:
                c.add_indirect_callees_from_file(tmp)
                mock_warn.assert_called_once()
        finally:
            os.unlink(tmp)

    def test_empty_indirect_callees_list(self):
        c = _make_collector_with_functions(
            ("caller_func", "0x1000"),
        )
        tmp = _write_json({"version": 1, "indirect_callees": []})
        try:
            # should not raise, not warn
            with patch("puncover.collector.warning") as mock_warn:
                c.add_indirect_callees_from_file(tmp)
                mock_warn.assert_not_called()
        finally:
            os.unlink(tmp)

    def test_missing_indirect_callees_key(self):
        c = _make_collector_with_functions(
            ("caller_func", "0x1000"),
        )
        tmp = _write_json({"version": 1})
        try:
            with patch("puncover.collector.warning") as mock_warn:
                c.add_indirect_callees_from_file(tmp)
                mock_warn.assert_not_called()
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
