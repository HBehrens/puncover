import json
import os
from pprint import pprint
import re
import shutil
import datetime
import jinja2
import collector

KEY_OUTPUT_FILE_NAME = "output_file_name"

@jinja2.contextfilter
def path_filter(context, file_name):
    if context and file_name:
        current_file = context.parent[KEY_OUTPUT_FILE_NAME]
        if current_file:
            current_file = os.path.dirname(current_file)
            return os.path.relpath(file_name, current_file)

    return file_name

def renderer_from_context(context):
    if isinstance(context, HTMLRenderer):
        return context
    if context:
        return context.parent.get("renderer", None)

    return None

def symbol_file(value):
    return value.get(collector.BASE_FILE, '__builtin')

@jinja2.contextfilter
def symbol_url_filter(context, value):
    # renderer = renderer_from_context(context)
    # if renderer:
    #     return path_filter(context, renderer.url_for_symbol_name(value))

    file_name = os.path.join(symbol_file(value), "symbol_%s.html" % value["name"])
    return path_filter(context, file_name)

@jinja2.contextfilter
def symbol_file_url_filter(context, value):
    return path_filter(context, os.path.join(symbol_file(value), "index.html"))

@jinja2.contextfilter
def assembly_filter(context, value):
    def linked_symbol_name(name):
        if context:
            renderer = context.parent.get("renderer", None)
            url = renderer.url_for_symbol_name(name, context)
            if url:
                return '<a href="%s">%s</a>' % (url, name)
        return name

    #   b8:	f000 f8de 	bleq	278 &lt:__aeabi_dmul+0x1dc&gt:
    pattern = re.compile(r"&lt;(\w+)")
    value = str(value)
    s = pattern.sub(lambda match: "&lt;"+linked_symbol_name(match.group(1)), value)
    return s
    # return str("&lt;")


class JSONRenderer:

    def __init__(self, c):
        self.collector = c

    def render(self, base_dir=None):
        symbols_by_file = {}
        entries = []
        for symbol in self.collector.all_symbols():
            if symbol.has_key(collector.FILE) and symbol.has_key(collector.LINE):
                entry = {
                    "name": symbol[collector.NAME],
                    "line": symbol[collector.LINE],
                }
                if symbol.get(collector.STACK_SIZE):
                    # TODO: stack qualifier
                    entry["short_text"] = "%d %d" % (symbol[collector.SIZE], symbol[collector.STACK_SIZE])
                    entry["long_text"] = "size: %d, stack size: %d" % (symbol[collector.SIZE], symbol[collector.STACK_SIZE])
                else:
                    entry["short_text"] = "%d" % symbol[collector.SIZE]
                    entry["long_text"] = "size: %d" % symbol[collector.SIZE]

                file_name = symbol[collector.FILE]
                if base_dir:
                    file_name = os.path.relpath(file_name, base_dir)
                entries = symbols_by_file.get(file_name, [])
                entries.append(entry)
                symbols_by_file[file_name] = entries
        data = {
            "meta": {
                "timestamp": datetime.datetime.now().isoformat(" "),
            },
            "symbols_by_file": symbols_by_file,
        }

        return json.dumps(data, indent=2, sort_keys=True)


class HTMLRenderer:

    def __init__(self, c):
        self.collector = c
        self.template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), "templates"))
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["symbol_url"] = symbol_url_filter
        self.template_env.filters["symbol_file_url"] = symbol_file_url_filter
        self.template_env.filters["assembly"] = assembly_filter
        self.template_env.filters["path"] = path_filter

        self.template_vars = {
            "renderer": self,
            "all_symbols": c.all_symbols(),
            "all_functions": c.all_functions(),
            "all_variables": c.all_variables(),
        }

    def render_overview(self, file_name):
        return self.render_template("overview.html", file_name)

    def render_template(self, template_name, file_name):
        self.template_vars[KEY_OUTPUT_FILE_NAME] = file_name
        template = self.template_env.get_template(template_name + ".jinja")
        output = template.render(self.template_vars)
        return output

    def render_symbol(self, symbol, file_name):
        self.template_vars["symbol"] = symbol
        return self.render_template("symbol.html", file_name)

    def render_file(self, file_name, symbols, output_file_name):
        self.template_vars["file_name"] = file_name
        for k in ["symbols", "functions", "variables"]:
            self.template_vars[k] = symbols[k]
        return self.render_template("file.html", output_file_name)

    def copy_static_assets_to_path(self, output_dir):
        def handle_static(input, output):
            output = os.path.join(output_dir, output)
            if os.path.exists(output):
                shutil.rmtree(output)

            shutil.copytree(os.path.join(os.path.dirname(__file__), input), output)

        handle_static("templates/css", "css")
        handle_static("templates/js", "js")

    def url_for_symbol_name(self, name, context=None):
        symbol = self.collector.symbol(name, False)
        return symbol_url_filter(context, symbol) if symbol else None

    # file_name = os.path.join(value.get(collector.BASE_FILE, '__builtin'), "symbol_%s.html" % value["name"])
    # return path_filter(context, file_name)


    def render_to_path(self, output_dir):
        # todo: collect files that exist before and delete them afterwards if they hadn't been regenerated

        def ensure_path(p):
            if not os.path.exists(p):
                os.makedirs(p)

        def write(name, content):
            if name:
                file_name = os.path.join(output_dir, name)
                ensure_path(os.path.dirname(file_name))

                with open(file_name, "w") as f:
                    f.write(content)

        ensure_path(output_dir)
        self.copy_static_assets_to_path(output_dir)

        # pprint(self.collector.all_symbols())

        write("index.html", self.render_overview("index.html"))

        containing_files = {}
        for s in self.collector.all_symbols():
            c_file = symbol_file(s)
            symbols_on_file = containing_files[c_file] = containing_files.get(c_file, {
                "symbols": [], "functions": [], "variables": [], "others": []
            })
            symbols_on_file["symbols"].append(s)
            type = s.get(collector.TYPE, "other")
            symbols_on_file[type +"s"].append(s)

            if type == collector.TYPE_FUNCTION:
                html_file = symbol_url_filter(None, s)
                write(html_file, self.render_symbol(s, html_file))

        for f, symbols in containing_files.items():
            html_file = symbol_file_url_filter(None, symbols["symbols"][0])
            write(html_file, self.render_file(f, symbols, html_file))
