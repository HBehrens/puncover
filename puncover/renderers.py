
# Python3.10 moved this module, support both import paths
try:
    from collections import Iterable
except ImportError:
    from collections.abc import Iterable

import itertools
import re
import pathlib

import jinja2
import markupsafe
from flask import abort, redirect, render_template, request
from flask.helpers import url_for
from flask.views import View
from werkzeug.urls import Href

from puncover import collector
from puncover.backtrace_helper import BacktraceHelper

KEY_OUTPUT_FILE_NAME = "output_file_name"

def renderer_from_context(context):
    if isinstance(context, HTMLRenderer):
        return context
    if context:
        return context.parent.get("renderer", None)

    return None

def symbol_file(value):
    return value.get(collector.BASE_FILE, '__builtin')

@jinja2.pass_context
def symbol_url_filter(context, value):
    renderer = renderer_from_context(context)
    if renderer:
        return renderer.url_for_symbol(value)

    return None

@jinja2.pass_context
def symbol_file_url_filter(context, value):
    f = value.get(collector.FILE, None)
    return symbol_url_filter(context, f) if f else None

def none_sum(a, b):
    if a is not None:
        return a + b if b is not None else a
    return b

def symbol_traverse(s, func):
    if isinstance(s, list):
        result = None
        for si in [symbol_traverse(i, func) for i in s]:
            if si is not None:
                result = none_sum(result, si)
        return result

    if collector.TYPE in s:
        if s[collector.TYPE] == collector.TYPE_FILE:
            return sum([symbol_traverse(s, func) for s in s[collector.SYMBOLS]])
        if s[collector.TYPE] == collector.FOLDER:
            return sum([symbol_traverse(s, func) for s in itertools.chain(s[collector.SUB_FOLDERS], s[collector.FILES])])

    return func(s)

def traverse_filter_wrapper(value, func):
    result = symbol_traverse(value, func)
    return result if result != 0 else ""

@jinja2.pass_context
def symbol_code_size_filter(context, value):
    return traverse_filter_wrapper(value, lambda s: s.get(collector.SIZE, None) if s.get(collector.TYPE, None) == collector.TYPE_FUNCTION else 0)

@jinja2.pass_context
def symbol_var_size_filter(context, value):
    return traverse_filter_wrapper(value, lambda s: s.get(collector.SIZE, None) if s.get(collector.TYPE, None) == collector.TYPE_VARIABLE else 0)

@jinja2.pass_context
def symbol_stack_size_filter(context, value, stack_base=None):
    if isinstance(stack_base, str):
        stack_base = None
    result = traverse_filter_wrapper(value, lambda s: s.get(collector.STACK_SIZE, None) if s.get(collector.TYPE, None) == collector.TYPE_FUNCTION else None)
    return none_sum(result, stack_base)

@jinja2.pass_context
def if_not_none_filter(context, value, default_value=""):
    return value if value is not None else default_value

@jinja2.pass_context
def unique_filter(context, value):
    if isinstance(value, Iterable):
        result = []
        for v in value:
            if v not in result:
                result.append(v)
        return result

    return value


@jinja2.pass_context
def assembly_filter(context, value):
    renderer = context.parent.get("renderer", None)
    def linked_symbol_name(name):
        if context:
            display_name = renderer.display_name_for_symbol_name(name)
            url = renderer.url_for_symbol_name(name, context)
            if url:
                return '<a href="%s">%s</a>' % (url, display_name)
        return name

    value = str(value)

    # Get a clean display name - and a URL - for symbol names in comments
    #   b8:	f000 f8de 	bleq	278 &lt:__aeabi_dmul+0x1dc&gt:
    pattern = re.compile(r"&lt;(\w+)")
    s = pattern.sub(lambda match: "&lt;"+linked_symbol_name(match.group(1)), value)

    # Get a clean display name for symbol names in labels
    # _ZN6Stream9readBytesEPcj():
    # FIXME: Unfortunately symbols that have been inlined will not be in our global
    # symbol name list and we will not be able to unmangle them (this is only a problem
    # for c++ symbols).
    pattern = re.compile(r"^(_.*)\(\):$")

    def display_name_for_label(match):
        display_name = renderer.display_name_for_symbol_name(match.group(1))

        if display_name.endswith(")"):
            # C++ symbols will include parenthesis and arguments
            return display_name + ":"
        else:
            # Other symbols will just have a name
            return display_name + "():"
    s = pattern.sub(display_name_for_label, s)

    return s
    # return str("&lt;")

@jinja2.pass_context
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

@jinja2.pass_context
def chain_filter(context, value, second_value=None):
    return list(itertools.chain(value, second_value if second_value else []))


def is_int_ge(x, cmp):
    return isinstance(x, int) and x >= cmp


@jinja2.pass_context
def bytes_filter(context, x):
    if not is_int_ge(x, 0):
        return x

    result = ''
    while x >= 1000:
        x, r = divmod(x, 1000)
        result = '<span class="secondary">,</span>%03d%s' % (r, result)
    return "%d%s" % (x, result)


@jinja2.pass_context
def style_background_bar_filter(context, x, total, color=None):
    if not is_int_ge(x, 1) or not is_int_ge(total, 1):
        return ''

    if color is None:
        color = 'rgba(0,0,255,0.07)'

    x = min(x, total)
    percent = 100 * x // total
    return 'background:linear-gradient(90deg, {1} {0}%, transparent {0}%);'.format(percent, color)

@jinja2.pass_context
def col_sortable_filter(context, title, is_alpha=False, id=None):

    id = title if id is None else id
    id = id.lower()

    # when sorting for numbers, we're interested in large numbers first
    next_sort = 'asc' if is_alpha else 'desc'
    sort_id, sort_order = context.parent.get('sort', 'a_b').split('_')
    classes = ['sortable']
    if sort_id.lower() == id:
        sort_class = 'sort_' + sort_order
        next_sort = 'desc' if sort_order == 'asc' else 'asc'
        if is_alpha:
            sort_class += '_alpha'
        classes.append(sort_class)

    next_sort = id + '_' + next_sort

    # replace/set ?sort= in URL
    args = request.args.copy()
    args['sort'] = next_sort
    url = Href(request.base_url, sort=True)

    return '<a href="%s" class="%s">%s</a>' % (url(args), ' '.join(classes), title)


@jinja2.pass_context
def sorted_filter(context, symbols):
    sort_id, sort_order = context.parent['sort'].split('_')

    def to_num(v):
        if v is None or v == '':
            return 0
        return int(v)

    key = {
        'name': lambda e: e.get(collector.DISPLAY_NAME, e.get(collector.NAME, None)).lower(),
        'code': lambda e: to_num(symbol_code_size_filter(context, e)),
        'stack': lambda e: to_num(symbol_stack_size_filter(context, e)),
        'vars': lambda e: to_num(symbol_var_size_filter(context, e)),
    }[sort_id]

    return list(sorted(symbols, key=key, reverse=(sort_order == 'desc')))


class HTMLRenderer(View):

    def __init__(self, collector):
        self.collector = collector
        self.template_vars = {
            "renderer": self,
            "SLASH": '<span class="slash">/</span>',
            "root_folders": list(collector.root_folders()),
            "sort": 'name_asc',
            "all_symbols": collector.all_symbols(),
            "all_functions": collector.all_functions(),
            "all_variables": collector.all_variables(),
        }

    def render_template(self, template_name, file_name):
        self.template_vars['sort'] = request.args.get('sort', 'name_asc')
        self.template_vars['request'] = request
        self.template_vars[KEY_OUTPUT_FILE_NAME] = file_name
        return render_template(template_name, **self.template_vars)

    def url_for_symbol_name(self, name, context=None):
        symbol = self.collector.symbol(name, False)
        return symbol_url_filter(context, symbol) if symbol else None

    def display_name_for_symbol_name(self, name):
        symbol = self.collector.symbol(name, False)
        return symbol['display_name'] if symbol else name

    def url_for(self, endpoint, **values):
        result = url_for(endpoint, **values)
        href = Href(result)
        # pass along any query parameters
        # this is kind of hacky as it replaces any existing parameters
        return href(request.args)

    def url_for_symbol(self, value):
        if value[collector.TYPE] in [collector.TYPE_FUNCTION]:
            return self.url_for("path", path=self.collector.qualified_symbol_name(value))

        # file or folder
        path = value.get(collector.PATH, None)
        return self.url_for("path", path=path) if path else ""


    def dispatch_request(self):
        return self.render_template(self.template, "index.html")


class OverviewRenderer(HTMLRenderer):

    def dispatch_request(self):
        return self.render_template("overview.html.jinja", "index.html")


class PathRenderer(HTMLRenderer):

    def dispatch_request(self, path=None):
        if path.endswith("/"):
            path = path[:-1]

        generic_path = pathlib.Path(path)
        symbol = self.collector.symbol(path)

        if symbol:
            self.template_vars["symbol"] = symbol
            return self.render_template("symbol.html.jinja", "symbol")

        file_element = self.collector.file_elements.get(generic_path, None)
        if file_element and file_element[collector.TYPE] == collector.TYPE_FILE:
            self.template_vars["file"] = file_element
            return self.render_template("file.html.jinja", path)
        elif file_element and file_element[collector.TYPE] == collector.TYPE_FOLDER:
            self.template_vars["folder"] = file_element
            return self.render_template("folder.html.jinja", path)

        print("### " + path)
        for f in sorted([f[collector.PATH] for f in self.collector.file_elements.values()]):
            print(f)
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

        return redirect(self.url_for("path", path=self.collector.qualified_symbol_name(symbol)))

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
    jinja_env.filters["if_not_none"] = if_not_none_filter
    jinja_env.filters["unique"] = unique_filter
    jinja_env.filters["assembly"] = assembly_filter
    jinja_env.filters["symbols"] = symbols_filter
    jinja_env.filters["chain"] = chain_filter
    jinja_env.filters["bytes"] = bytes_filter
    jinja_env.filters["style_background_bar"] = style_background_bar_filter
    jinja_env.filters["col_sortable"] = col_sortable_filter
    jinja_env.filters["sorted"] = sorted_filter



def register_urls(app, collector):
    app.add_url_rule("/", view_func=OverviewRenderer.as_view("overview", collector=collector))
    app.add_url_rule("/all/", view_func=AllSymbolsRenderer.as_view("all", collector=collector))
    app.add_url_rule("/path/<path:path>/", view_func=PathRenderer.as_view("path", collector=collector))
    app.add_url_rule("/symbol/<string:symbol_name>", view_func=SymbolRenderer.as_view("symbol", collector=collector))
    app.add_url_rule("/rack/", view_func=RackRenderer.as_view("rack", collector=collector), methods=["GET", "POST"])
