import unittest

from mock.mock import Mock, patch
from flask import globals
from puncover import renderers


class TestRenderer(unittest.TestCase):

    def setUp(self):
        self.request = Mock(name='request')
        self.request.args = {}
        self.request.base_url = 'http://puncover.com'
        self.request.blueprint = None

        def url_adapter_func(url, *args, **kwargs):
            return url

        reqctx = Mock(name='reqctx')
        reqctx.request = self.request
        reqctx.url_adapter = Mock(name='url_adapter')
        reqctx.url_adapter.build = Mock(side_effect=url_adapter_func)
        globals._request_ctx_stack.push(reqctx)

        self.appctx = Mock(name='appctx')
        globals._app_ctx_stack.push(self.appctx)

    def tearDown(self):
        globals._request_ctx_stack.pop()
        globals._app_ctx_stack.pop()

    def test_bytes_filter_ignores(self):
        f = renderers.bytes_filter
        self.assertEqual(1234.56, f({}, 1234.56))
        self.assertEqual(None, f({}, None))
        self.assertEqual('foo', f({}, 'foo'))
        self.assertEqual(-2, f({}, -2))

    def test_bytes_filter(self):
        f = renderers.bytes_filter
        self.assertEqual('0', f({}, 0))
        self.assertEqual('999', f({}, 999))
        self.assertEqual('1<span class="secondary">,</span>234', f({}, 1234))
        self.assertEqual('12<span class="secondary">,</span>345<span class="secondary">,</span>678', f({}, 12345678))

    def test_style_background_bar_filter_ignores(self):
        f = renderers.style_background_bar_filter
        self.assertEqual('', f({}, 'foo', 123))
        self.assertEqual('', f({}, 10, 'foo'))

    def test_style_background_bar_filter(self):
        f = renderers.style_background_bar_filter
        expected = 'background:linear-gradient(90deg, rgba(0,0,255,0.07) 8%, transparent 8%);'
        self.assertEqual(expected, f({}, 10, 123))

        expected = 'background:linear-gradient(90deg, black 100%, transparent 100%);'
        self.assertEqual(expected, f({}, 200, 123, 'black'))

    def test_sorted_filter_name(self):
        ctx = Mock()
        ctx.parent = {'sort': 'name_asc'}
        a = {'display_name': 'a'}
        b = {'name': 'b'}
        c = {'display_name': 'C'}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([a, b, c], actual)

        ctx.parent = {'sort': 'name_desc'}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_sorted_filter_code(self):
        ctx = Mock()
        ctx.parent = {'sort': 'code_asc'}
        a = {'type': 'folder', 'sub_folders': [], 'files': [
        ]}
        b = {'type': 'file', 'symbols': [
            {'type': 'function', 'size': 200}
        ]}
        c = {'type': 'file', 'symbols': [
            {'type': 'function', 'size': 300}
        ]}
        actual = renderers.sorted_filter(ctx, [b, c, a])

        self.assertEqual([a, b, c], actual)

        ctx.parent = {'sort': 'code_desc'}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_sorted_filter_vars(self):
        ctx = Mock()
        ctx.parent = {'sort': 'vars_asc'}
        a = {'type': 'folder', 'sub_folders': [], 'files': [
        ]}
        b = {'type': 'file', 'symbols': [
            {'type': 'variable', 'size': 200}
        ]}
        c = {'type': 'file', 'symbols': [
            {'type': 'variable', 'size': 300}
        ]}
        actual = renderers.sorted_filter(ctx, [b, c, a])

        self.assertEqual([a, b, c], actual)

        ctx.parent = {'sort': 'vars_desc'}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_sorted_filter_stack(self):
        ctx = Mock()
        ctx.parent = {'sort': 'stack_asc'}
        a = {'type': 'folder', 'sub_folders': [], 'files': [
        ]}
        b = {'type': 'file', 'symbols': [
            {'type': 'function', 'stack_size': 200}
        ]}
        c = {'type': 'file', 'symbols': [
            {'type': 'function', 'stack_size': 300}
        ]}
        actual = renderers.sorted_filter(ctx, [b, c, a])

        self.assertEqual([a, b, c], actual)

        ctx.parent = {'sort': 'stack_desc'}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_col_sortable_filter_name(self):
        ctx = Mock()
        ctx.parent = {}
        self.request.args = {'foo': 'bar'}

        expected = '<a href="http://puncover.com?foo=bar&sort=name_asc" class="sortable">Name</a>'
        actual = renderers.col_sortable_filter(ctx, 'Name', True)
        self.assertEqual(expected, actual)

        # if current sort is ascending,
        # mark as sorted ascending and populate link for descending
        ctx.parent = {'sort': 'name_asc'}
        self.request.args = {'sort': 'foo'}
        expected = '<a href="http://puncover.com?sort=name_desc" class="sortable sort_asc_alpha">Name</a>'
        actual = renderers.col_sortable_filter(ctx, 'Name', True)
        self.assertEqual(expected, actual)

    def test_col_sortable_filter_stack(self):
        ctx = Mock()
        ctx.parent = {}
        self.request.args = {'foo': 'bar'}

        expected = '<a href="http://puncover.com?foo=bar&sort=stack_asc" class="sortable">Stack</a>'
        actual = renderers.col_sortable_filter(ctx, 'Stack', True)
        self.assertEqual(expected, actual)

        # if current sort is ascending,
        # mark as sorted ascending and populate link for descending
        ctx.parent = {'sort': 'stack_asc'}
        self.request.args = {'sort': 'foo'}
        expected = '<a href="http://puncover.com?sort=stack_desc" class="sortable sort_asc_alpha">Stack</a>'
        actual = renderers.col_sortable_filter(ctx, 'Stack', True)
        self.assertEqual(expected, actual)

    def test_url_for(self):
        c = Mock()
        c.root_folders = Mock(return_value=[])
        c.all_symbols = Mock(return_value=[])
        c.all_functions = Mock(return_value=[])
        c.all_variables = Mock(return_value=[])
        c = renderers.HTMLRenderer(c)

        actual = c.url_for('/')
        self.assertEqual('/', actual)

        # preserves query parameters
        self.request.args = {'foo': 'bar'}
        actual = c.url_for('/')
        self.assertEqual('/?foo=bar', actual)
