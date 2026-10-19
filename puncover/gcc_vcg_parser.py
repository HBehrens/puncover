import re

from pydantic import BaseModel
from pydantic.experimental.missing_sentinel import MISSING

NO_WORST_STACK_SIZE_YET = -1
GCC_INDIRECT_CALL_LABEL = "__indirect_call"


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
    sourcename: str
    targetname: str
    label: str | None | MISSING = MISSING


class VCG_Graph(BaseModel):
    title: str
    nodes: list[VCG_Node]
    edges: list[VCG_Edge]


class FunctionCalleeEntry(BaseModel):
    title: str
    node: VCG_Node
    node_declaration: str | None | MISSING = MISSING
    node_definition: str | None | MISSING = MISSING
    edges: list[VCG_Edge]
    worst_stack_use: int
    visited: bool


class FunctionCallTree(BaseModel):
    root: FunctionCalleeEntry
    node_declaration: str | None | MISSING = MISSING
    node_definition: str | None | MISSING = MISSING
    edges: list[VCG_Edge]


def deepest_call_tree(
    f: FunctionCalleeEntry, fn_callee_map: dict[str, FunctionCalleeEntry], visited=None
):
    if f.worst_stack_use != NO_WORST_STACK_SIZE_YET:
        return (f.worst_stack_use, [])
    visited = [f] + (visited if visited else [])
    result = (0, [])

    for call_edge in f.edges:
        fn_target_name_and_path = call_edge.targetname.split(":", 1)
        callee_name = call_edge.targetname
        if callee_name not in fn_callee_map and len(fn_target_name_and_path) == 2:
            callee_name = fn_target_name_and_path[1]
        if "." in callee_name:  # removes .constprop.0, .isra, ...
            split_dots = callee_name.split(".")
            callee_name = split_dots[0]
        if callee_name not in fn_callee_map:
            continue
        callee_node = fn_callee_map[callee_name]
        if callee_node not in visited:
            candidate = deepest_call_tree(callee_node, fn_callee_map, visited)
            if candidate[0] > result[0]:
                result = candidate

    stack_size = f.node.label.stack_size if isinstance(f.node.label.stack_size, int) else 0
    result = (result[0] + stack_size, [f] + result[1])
    f.worst_stack_use = stack_size
    return result


class VCG_Parser:
    su_marker_pattern = r"(\d+)\s+bytes\s+\((.*?)\)"

    def parse_vcg_label_attributes(self, label_str: str):
        vcg_label_lines = label_str.split("\\n")

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
        sourcename = attributes["sourcename"] if "sourcename" in attributes else None
        targetname = attributes["targetname"] if "targetname" in attributes else None
        label = attributes["label"] if "label" in attributes else None
        if sourcename and targetname:
            return VCG_Edge(sourcename=sourcename, targetname=targetname, label=label)
        else:
            # TODO log error/warning or empty ok?
            return VCG_Edge()

    def parse_vcg_graph(self, graph_str: str):
        lines = graph_str.splitlines()
        # looked at gcc/toplev.cc::lang_dependent_init
        # assume exactly one edge / node per line and graph+title in first line
        graph_decl = lines[0] if len(lines) >= 1 else ""
        title = ""
        # strip graph+title and quotes
        if graph_decl.startswith("graph: { title: "):
            title = graph_decl.replace("graph: { title: ", "")
            title = title[1:-1]
        else:
            pass  # TODO error log

        nodes = []
        edges = []
        for line in lines[1:]:
            line = line[:-2] if line.endswith(" }") else line
            if line.startswith("node: { "):
                node_str = line.replace("node: { ", "")
                n = self.parse_node(node_str)
                nodes += [n]
            elif line.startswith("edge: { "):
                edge_str = line.replace("edge: { ", "")
                e = self.parse_edge(edge_str)
                edges += [e]
            elif line.startswith("}"):
                break

        graph = VCG_Graph(title=title, edges=edges, nodes=nodes)
        return graph
