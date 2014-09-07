import json
import os
import shutil
import jinja2
import collector


@jinja2.contextfilter
def path_filter(context, file_name):
    if context:
        current_file = os.path.dirname(context.parent["file_name"])
        return os.path.relpath(file_name, current_file)
    else:
        return file_name

@jinja2.contextfilter
def symbol_url_filter(context, value):
    file_name = os.path.join(value.get(collector.BASE_FILE, '__builtin'), "symbol_%s.html" % value["name"])
    return path_filter(context, file_name)


class JSONRenderer:

    def __init__(self, c):
        self.collector = c

    def render(self):
        data = []
        for symbol in self.collector.all_symbols():
            if symbol.has_key(collector.FILE) and symbol.has_key(collector.LINE):
                entry = {}
                for key in [collector.NAME, collector.BASE_FILE, collector.LINE, collector.STACK_SIZE, collector.SIZE]:
                    if symbol.has_key(key):
                        entry[key] = symbol[key]
                data.append(entry)

        return json.dumps(data, indent=2)


class HTMLRenderer:

    def __init__(self, c):
        self.collector = c
        self.template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), "templates"))
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["symbol_url"] = symbol_url_filter
        self.template_env.filters["path"] = path_filter

        self.template_vars = {
            "symbols": c.all_symbols(),
            "functions": c.all_functions(),
            "functions_with_size": list(reversed(sorted([s for s in c.all_functions() if s.has_key(collector.SIZE)], key=lambda s: s[collector.SIZE])))
        }

    def render_overview(self, file_name):
        return self.render_template("overview.html", file_name)

    def render_template(self, template_name, file_name):
        self.template_vars["file_name"] = file_name
        template = self.template_env.get_template(template_name + ".jinja")
        output = template.render(self.template_vars)
        return output

    def render_symbol(self, symbol, file_name):
        self.template_vars["symbol"] = symbol
        return self.render_template("symbol.html", file_name)

    def render_file(self, file_name):
        return self.render_template("file.html", file_name)

    def copy_static_assets_to_path(self, output_dir):
        css_output = os.path.join(output_dir, "css")
        if os.path.exists(css_output):
            shutil.rmtree(css_output)

        shutil.copytree(os.path.join(os.path.dirname(__file__), "templates/css"), css_output)

    def render_to_path(self, output_dir):
        # todo: collect files that exist before and delete them afterwards if they hadn't been regenerated

        def ensure_path(p):
            if not os.path.exists(p):
                os.makedirs(p)

        def write(name, content):
            file_name = os.path.join(output_dir, name)
            ensure_path(os.path.dirname(file_name))

            with open(file_name, "w") as f:
                f.write(content)

        ensure_path(output_dir)
        self.copy_static_assets_to_path(output_dir)

        write("index.html", self.render_overview("index.html"))

        # todo: render file overview

        # todo: only render functions
        for s in self.collector.symbols.values():
            file_name = symbol_url_filter(None, s)
            write(file_name, self.render_symbol(s, file_name))
