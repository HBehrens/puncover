import re
import collector

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

