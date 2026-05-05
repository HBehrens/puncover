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

from pydantic import BaseModel, Field, RootModel
from pydantic.experimental.missing_sentinel import MISSING
from pydantic.json_schema import GenerateJsonSchema

SCHEMA_PATH = Path(__file__).parent / "report_schema.json"


class CallFrame(BaseModel):
    function: str
    name: str
    stack_size: Union[int, str]  # "???" when the frame's stack size is unknown


class FunctionStackReport(BaseModel):
    max_static_stack_size: int
    call_stack: list[CallFrame]
    max_stack_size: int | MISSING = MISSING  # only present when user supplied a limit via :::


class FunctionCall(BaseModel):
    from_addr: int = Field(serialization_alias="from", alias="from", validation_alias="from")
    to: int | MISSING = MISSING
    dynamic: bool


class FunctionSymbol(BaseModel):
    name: str
    file: str | MISSING = MISSING
    line: int | MISSING = MISSING
    address: int
    section_index: int | MISSING = MISSING
    size: int
    callers: list[FunctionCall] | MISSING = MISSING
    callees: list[FunctionCall] | MISSING = MISSING
    called_from_other_file: bool | MISSING = MISSING
    stack_size: int | MISSING = MISSING
    stack_qualifiers: str | MISSING = MISSING
    disasm: list[str] | MISSING = MISSING
    asm: str | MISSING = MISSING


class VariableSymbol(BaseModel):
    name: str
    file: str | MISSING = MISSING
    line: int | MISSING = MISSING
    address: int
    section_index: int | MISSING = MISSING
    size: int
    type: str | MISSING = MISSING


class TagEntry(BaseModel):
    timestamp: str
    stack_report: dict[str, FunctionStackReport] | MISSING = MISSING
    functions: list[FunctionSymbol] | MISSING = MISSING
    variables: list[VariableSymbol] | MISSING = MISSING


class Report(RootModel[dict[str, TagEntry]]):
    """Top-level report: keys are report tags, values are tagged run entries."""


def generate_schema() -> dict:
    schema = Report.model_json_schema()
    schema["$schema"] = GenerateJsonSchema.schema_dialect
    return schema


def write_schema(path: Path = SCHEMA_PATH) -> None:
    schema = generate_schema()
    path.write_text(json.dumps(schema, indent=2) + "\n")


if __name__ == "__main__":
    write_schema()
    print(f"Schema written to {SCHEMA_PATH}")
