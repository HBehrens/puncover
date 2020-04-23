import re
from puncover import collector

class BacktraceHelper():

    def __init__(self, collector):
        self.collector = collector

    derive_functions_symbols_pattern = re.compile(r"\b(\w+)\b")

    def derive_function_symbols(self, text):
        result = []
        for f in self.derive_functions_symbols_pattern.finditer(text):
            s = self.collector.symbol(f.group(1), False)
            if s and s[collector.TYPE] == collector.TYPE_FUNCTION:
                result.append(s)
        return result

    def transform_known_symbols(self, text, transformer):
        def f(match):
            symbol_name = match.group(1)
            symbol = self.collector.symbol(symbol_name, False)
            return transformer(symbol) if symbol else symbol_name

        return self.derive_functions_symbols_pattern.sub(f, text)


    def deepest_call_tree(self, f, list_attribute, cache_attribute, visited = None):
        # TODO: find strongly connected components and count cycles correctly
        if cache_attribute in f:
            return f[cache_attribute]

        visited = [f] + (visited if visited else [])
        result = (0, [])

        for c in f[list_attribute]:
            if c not in visited:
                candidate = self.deepest_call_tree(c, list_attribute, cache_attribute, visited)
                if candidate[0] > result[0]:
                    result = candidate


        result = (result[0] + f.get(collector.STACK_SIZE, 0), [f] + result[1])
        f[cache_attribute] = result
        return result


    def deepest_callee_tree(self, f):
        return self.deepest_call_tree(f, collector.CALLEES, collector.DEEPEST_CALLEE_TREE)

    def deepest_caller_tree(self, f):
        return self.deepest_call_tree(f, collector.CALLERS, collector.DEEPEST_CALLER_TREE)
