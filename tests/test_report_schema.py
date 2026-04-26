import json
import unittest

from puncover import collector
from puncover.collector import Collector
from puncover.report_schema import (
    SCHEMA_PATH,
    Report,
    TagEntry,
    generate_schema,
)


class TestSchemaInSync(unittest.TestCase):
    """Verify the committed schema.json matches the current Pydantic models."""

    def test_committed_schema_matches_models(self):
        committed = json.loads(SCHEMA_PATH.read_text())
        generated = generate_schema()
        self.assertEqual(
            committed,
            generated,
            "report_schema.json is out of sync with the Pydantic models. "
            "Run `python -m puncover.report_schema` to regenerate it.",
        )


class TestSchemaValidatesOutput(unittest.TestCase):
    """Verify that report output actually conforms to the schema."""

    def _make_report(self, entries, report_type="json"):
        from puncover.backtrace_helper import BacktraceHelper

        cc = Collector(None)
        thread_fn = cc.add_symbol(
            "thread_fn", "0x0001", type=collector.TYPE_FUNCTION, stack_size=10
        )
        callee_fn = cc.add_symbol(
            "callee_fn", "0x0002", type=collector.TYPE_FUNCTION, stack_size=20
        )
        thread_fn[collector.DISPLAY_NAME] = "thread_fn"
        callee_fn[collector.DISPLAY_NAME] = "callee_fn"
        cc.enhance_call_tree()
        cc.add_function_call(thread_fn, callee_fn)

        h = BacktraceHelper(cc)
        for f in cc.all_functions():
            h.deepest_callee_tree(f)
            h.deepest_caller_tree(f)

        return cc.report_max_static_stack_usages_from_function_names(entries, report_type)

    def test_report_output_valid_against_schema(self):
        stack_report = self._make_report(["thread_fn:::64"])

        # Build a full tagged report dict as puncover.py would write it
        report_data = {
            "ci_build_42": TagEntry(
                timestamp="2024-01-01T00:00:00",
                stack_report=stack_report,  # type: ignore[arg-type]
            ).model_dump()
        }

        # model_validate parses and raises ValidationError if structure is wrong
        Report.model_validate(report_data)

    def test_report_output_without_stack_limit_is_valid(self):
        stack_report = self._make_report(["thread_fn"])

        report_data = {
            "no_tag": TagEntry(
                timestamp="2024-01-01T00:00:00",
                stack_report=stack_report,  # type: ignore[arg-type]
            ).model_dump(exclude_none=True)
        }

        Report.model_validate(report_data)

    def test_report_without_stack_report_is_valid(self):
        report_data = {
            "no_tag": {"timestamp": "2024-01-01T00:00:00"},
        }
        Report.model_validate(report_data)
