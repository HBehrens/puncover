import re

from pydantic import BaseModel
from pydantic.experimental.missing_sentinel import MISSING


# TODO add dynamic allocation parsing?
class VCG_Label(BaseModel):
    file_name: str | None | MISSING = MISSING
    function_name: str | None | MISSING = MISSING
    line: int | None | MISSING = MISSING
    column: int | None | MISSING = MISSING
    stack_size: int | None | MISSING = MISSING
    stack_qualifier: str | None | MISSING = MISSING


class VCG_Node(BaseModel):
    title: str | None | MISSING = MISSING
    label: VCG_Label | None | MISSING = MISSING


class VCG_Edge(BaseModel):
    sourcename: str | None | MISSING = MISSING
    targetname: str | None | MISSING = MISSING
    label: str | None | MISSING = MISSING


class VCG_Parser:
    su_marker_pattern = r"(\d+)\s+bytes\s+\((.*?)\)"

    # def __init__(self):
    #     pass

    def parse_vcg_label_attributes(self, label_str):
        vcg_label_lines = label_str.split("\n")

        function_name = vcg_label_lines[0] if len(vcg_label_lines) >= 1 else None
        fp_split = (
            vcg_label_lines[1].split(":") if len(vcg_label_lines) >= 2 else [None, None, None]
        )
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
            return VCG_Label(
                function_name=function_name,
            )
        if are_base_callgraph_attr_ok and len(vcg_label_lines) == 2:
            return VCG_Label(
                function_name=function_name,
                file_name=file_name,
                line=line,
                column=column,
            )
        elif are_base_callgraph_attr_ok and len(vcg_label_lines) >= 3:
            return VCG_Label(
                function_name=function_name,
                file_name=file_name,
                line=line,
                column=column,
                stack_size=stack_size,
                stack_qualifier=stack_qualifier,
            )
        else:
            # TODO log error/warning?
            return VCG_Label()

    def parse_vcg_attributes(self, attr_str):
        attribute_pattern = r'(\w+)\s*:\s*(?:"([^"]*)"|(\S+))'
        attributes = re.findall(attribute_pattern, attr_str)
        parsed_dict = {match[0]: match[1] if match[1] else match[2] for match in attributes}
        return parsed_dict

    def parse_node(self, node_str):
        attributes = self.parse_vcg_attributes(node_str)
        title = attributes["title"] if "title" in attributes else None
        label = attributes["label"] if "label" in attributes else None
        vcg_label = self.parse_vcg_label_attributes(label)
        if title and label:
            return VCG_Node(title=title, label=vcg_label)
        if title:
            return VCG_Node(title=title)
        else:
            return VCG_Node()

    def parse_edge(self, node_str):
        attributes = self.parse_vcg_attributes(node_str)
        print("zzz", attributes)
        sourcename = attributes["sourcename"] if "sourcename" in attributes else None
        targetname = attributes["targetname"] if "targetname" in attributes else None
        label = attributes["label"] if "label" in attributes else None
        if sourcename and targetname:
            return VCG_Edge(sourcename=sourcename, targetname=targetname, label=label)
        else:
            # TODO log error/warning or empty ok?
            return VCG_Edge()

    def parse_vcg_file(self, edge_str):
        pass
