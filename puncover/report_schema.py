"""
Pydantic models for the puncover JSON report format.

These models are the authoritative definition of the report structure.
The committed schema.json is generated from them; run this module directly
to regenerate it:

    python -m puncover.report_schema
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from pydantic import BaseModel, RootModel

SCHEMA_PATH = Path(__file__).parent / "report_schema.json"


class CallFrame(BaseModel):
    function: str
    name: str
    stack_size: Union[int, str]  # "???" when the frame's stack size is unknown


class FunctionStackReport(BaseModel):
    max_static_stack_size: int
    call_stack: list[CallFrame]
    max_stack_size: int | None = None  # only present when user supplied a limit via :::


class TagEntry(BaseModel):
    timestamp: str
    stack_report: dict[str, FunctionStackReport] | None = None


class Report(RootModel[dict[str, TagEntry]]):
    """Top-level report: keys are report tags, values are tagged run entries."""


def generate_schema() -> dict:
    return Report.model_json_schema()


def write_schema(path: Path = SCHEMA_PATH) -> None:
    schema = generate_schema()
    path.write_text(json.dumps(schema, indent=2) + "\n")


if __name__ == "__main__":
    write_schema()
    print(f"Schema written to {SCHEMA_PATH}")
