import os
import re
from flask import Flask, render_template, abort, redirect, request
import flask
from flask.helpers import url_for
from flask.views import View
import itertools
import jinja2
import markupsafe
from backtrace_helper import BacktraceHelper
import collector

KEY_OUTPUT_FILE_NAME = "output_file_name"

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
    renderer = renderer_from_context(context)
    if renderer:
        return renderer.url_for_symbol(value)

    return None

@jinja2.contextfilter
def symbol_file_url_filter(context, value):
    f = value.get(collector.FILE, None)
    return symbol_url_filter(context, f) if f else None

def symbol_traverse(s, func):
    if isinstance(s, list):
        return sum([symbol_traverse(i, func) for i in s])

    if collector.TYPE in s:
        if s[collector.TYPE] == collector.TYPE_FILE:
            return sum([symbol_traverse(s, func) for s in s[collector.SYMBOLS]])
        if s[collector.TYPE] == collector.FOLDER:
            return sum([symbol_traverse(s, func) for s in itertools.chain(s[collector.SUB_FOLDERS], s[collector.FILES])])

    return func(s)

def traverse_filter_wrapper(value, func):
    result = symbol_traverse(value, func)
    return result if result != 0 else ""

@jinja2.contextfilter
def symbol_code_size_filter(context ,value):
    return traverse_filter_wrapper(value, lambda s: s.get(collector.SIZE, 0) if s.get(collector.TYPE, None) == collector.TYPE_FUNCTION else 0)

@jinja2.contextfilter
def symbol_var_size_filter(context ,value):
    return traverse_filter_wrapper(value, lambda s: s.get(collector.SIZE, 0) if s.get(collector.TYPE, None) == collector.TYPE_VARIABLE else 0)

@jinja2.contextfilter
def symbol_stack_size_filter(context ,value):
    return traverse_filter_wrapper(value, lambda s: s.get(collector.STACK_SIZE, 0) if s.get(collector.TYPE, None) == collector.TYPE_FUNCTION else 0)


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

@jinja2.contextfilter
def symbols_filter(context, value):
    renderer = renderer_from_context(context)

    if renderer:
        helper = BacktraceHelper(renderer.collector)

        def make_links(s):
            name = s[collector.NAME]
            url = renderer.url_for_symbol_name(name, context)
            return '<a href="%s">%s</a>' % (url, name)

        if isinstance(value, markupsafe.Markup):
            value = value.__html__().unescape()
        return helper.transform_known_symbols(value, make_links)

    return value

@jinja2.contextfilter
def chain_filter(context, value, second_value=None):
    return list(itertools.chain(value, second_value if second_value else []))


class HTMLRenderer(View):

    def __init__(self, collector):
        self.collector = collector
        self.template_vars = {
            "renderer": self,
            "SLASH": '<span class="slash">/</span>',
            "root_folders": list(collector.root_folders()),
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

    def url_for_symbol(self, value):
        if value[collector.TYPE] in [collector.TYPE_FUNCTION]:
            return url_for("path", path=self.collector.qualified_symbol_name(value))

        # file or folder
        path = value.get(collector.PATH, None)
        return url_for("path", path=path) if path else ""


    def dispatch_request(self):
        return self.render_template(self.template, "index.html")


class OverviewRenderer(HTMLRenderer):

    def dispatch_request(self):
        return self.render_template("overview.html.jinja", "index.html")


class PathRenderer(HTMLRenderer):

    def dispatch_request(self, path=None):
        if path.endswith("/"):
            path = path[:-1]

        symbol = self.collector.symbol(path)
        if symbol:
            self.template_vars["symbol"] = symbol
            return self.render_template("symbol.html.jinja", "symbol")

        file_element = self.collector.file_elements.get(path, None)
        if file_element and file_element[collector.TYPE] == collector.TYPE_FILE:
            self.template_vars["file"] = file_element
            return self.render_template("file.html.jinja", path)
        elif file_element and file_element[collector.TYPE] == collector.TYPE_FOLDER:
            self.template_vars["folder"] = file_element
            return self.render_template("folder.html.jinja", path)

        print "### " + path
        for f in sorted([f[collector.PATH] for f in self.collector.file_elements.values()]):
            print f
        # print "## root folders"
        # for f in self.collector.root_folders():
        #     print f[collector.PATH]
        # print "## collapsed root folders"
        # for f in self.collector.collapsed_root_folders():
        #     print f[collector.PATH]

        abort(404)


class SymbolRenderer(HTMLRenderer):

    def dispatch_request(self, symbol_name=None):
        symbol = self.collector.symbol(symbol_name, qualified=False)
        if not symbol:
            abort(404)

        return redirect(url_for("path", path=self.collector.qualified_symbol_name(symbol)))

class AllSymbolsRenderer(HTMLRenderer):

    def dispatch_request(self, symbol_name=None):
        return self.render_template("all_symbols.html.jinja", "all")


class RackRenderer(HTMLRenderer):

    def dispatch_request(self, symbol_name=None):
        if request.method == "POST":
            helper = BacktraceHelper(self.collector)

            snippet = request.form["snippet"]
            self.template_vars["snippet"] = snippet
            self.template_vars["functions"] = helper.derive_function_symbols(snippet)

        return self.render_template("rack.html.jinja", "rack")


def register_jinja_filters(jinja_env):
    jinja_env.filters["symbol_url"] = symbol_url_filter
    jinja_env.filters["symbol_file_url"] = symbol_file_url_filter
    jinja_env.filters["symbol_code_size"] = symbol_code_size_filter
    jinja_env.filters["symbol_var_size"] = symbol_var_size_filter
    jinja_env.filters["symbol_stack_size"] = symbol_stack_size_filter
    jinja_env.filters["assembly"] = assembly_filter
    jinja_env.filters["symbols"] = symbols_filter
    jinja_env.filters["chain"] = chain_filter


def register_urls(app, collector):
    app.add_url_rule("/", view_func=OverviewRenderer.as_view("overview", collector=collector))
    app.add_url_rule("/all/", view_func=AllSymbolsRenderer.as_view("all", collector=collector))
    app.add_url_rule("/path/<path:path>/", view_func=PathRenderer.as_view("path", collector=collector))
    app.add_url_rule("/symbol/<string:symbol_name>", view_func=SymbolRenderer.as_view("symbol", collector=collector))
    app.add_url_rule("/rack/", view_func=RackRenderer.as_view("rack", collector=collector), methods=["GET", "POST"])
