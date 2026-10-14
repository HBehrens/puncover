import re

from pydantic import BaseModel, Field, RootModel
from pydantic.experimental.missing_sentinel import MISSING

# TODO add dynamic allocation parsing?
class VCGLabel(BaseModel):
    file_name: str | None | MISSING = MISSING
    function_name: str | None | MISSING = MISSING
    line: int | None | MISSING = MISSING
    column: int | None | MISSING = MISSING
    stack_size: int | None | MISSING = MISSING
    stack_qualifier: str | None | MISSING = MISSING

class VCG_Parser:
    su_marker_pattern = r"(\d+)\s+bytes\s+\((.*?)\)"

    # def __init__(self):
    #     pass

    def parse_vcg_label_attributes(self, label_str):
        vcg_label_lines = label_str.split("\n")

        function_name = vcg_label_lines[0] if len(vcg_label_lines) >= 1 else None
        fp_split = vcg_label_lines[1].split(":") if len(vcg_label_lines) >= 2 else [None, None, None]
        line = int(fp_split[-2]) if len(fp_split) >= 3 and fp_split[-2] else None
        column = int(fp_split[-1]) if len(fp_split) >= 3 and fp_split[-1] else None
        file_name = ":".join(fp_split[:-2]) if len(fp_split) >= 3 and fp_split[0] else None
        are_base_callgraph_attr_ok = function_name and line and column and file_name
        # callgraph with su MARKERS - Match stacksize and qualifier in i.e. '15 bytes (static)'
        stacksize_marker = vcg_label_lines[2] if len(vcg_label_lines) >= 3 else ""
        match = re.search(VCG_Parser.su_marker_pattern, stacksize_marker)
        stack_size = int(match.group(1)) if match else None
        stack_qualifier = match.group(2) if match else None

        if function_name and len(vcg_label_lines) == 1:
            return VCGLabel(
                function_name=function_name,
            )
        if are_base_callgraph_attr_ok and len(vcg_label_lines) == 2:
            return VCGLabel(
                function_name=function_name,
                file_name=file_name,
                line=line,
                column=column,
            )
        elif are_base_callgraph_attr_ok and len(vcg_label_lines) >= 3:
            return VCGLabel(
                function_name=function_name,
                file_name=file_name,
                line=line,
                column=column,
                stack_size=stack_size,
                stack_qualifier=stack_qualifier
            )
        else:
            # TODO log error/warning?
            return VCGLabel()

    def parse_vcg_attributes(self, attr_str):
        pass

    def parse_node(self, node_str):
        pass

    def parse_edge(self, edge_str):
        pass

    def parse_vcg_file(self, edge_str):
        pass
