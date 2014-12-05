import os
import re
from flask import Flask, render_template
from flask.views import View
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


class HTMLRenderer(View):

    def __init__(self, collector):
        self.collector = collector
        self.template_vars = {
            "renderer": self,
            "all_symbols": collector.all_symbols(),
            "all_functions": collector.all_functions(),
            "all_variables": collector.all_variables(),
        }

    def render_template(self, template_name, file_name):
        self.template_vars[KEY_OUTPUT_FILE_NAME] = file_name
        return render_template(template_name, **self.template_vars)

    def url_for_symbol_name(self, name, context=None):
        symbol = self.collector.symbol(name, False)
        return symbol_url_filter(context, symbol) if symbol else None

class OverviewRenderer(HTMLRenderer):

    def dispatch_request(self):
        return self.render_template("overview.html.jinja", "index.html")


class FileRenderer(HTMLRenderer):

    def dispatch_request(self, dir=None):
        return self.render_template("file.html.jinja", dir)


class SymbolRenderer(HTMLRenderer):

    def dispatch_request(self, symbol_name=None):
        symbol = self.collector.symbol(symbol_name, qualified=False)
        self.template_vars["symbol"] = symbol
        return self.render_template("symbol.html.jinja", "symbol")

def register_jinja_filters(jinja_env):
    jinja_env.filters["symbol_url"] = symbol_url_filter
    jinja_env.filters["symbol_file_url"] = symbol_file_url_filter
    jinja_env.filters["assembly"] = assembly_filter
    jinja_env.filters["path"] = path_filter


def register_urls(app, collector):
    app.add_url_rule("/", view_func=OverviewRenderer.as_view("overview", collector=collector))
    app.add_url_rule("/file/<string:dir>", view_func=FileRenderer.as_view("file", collector=collector))
    app.add_url_rule("/symbol/<string:symbol_name>", view_func=SymbolRenderer.as_view("symbol", collector=collector))
