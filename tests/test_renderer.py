import unittest
from unittest.mock import Mock, patch

from puncover import renderers


class TestRenderer(unittest.TestCase):
    def setUp(self):
        # Use a mock request object for tests
        self.request = Mock()
        self.request.args = {}
        self.request.base_url = "http://localhost/"
        self.request.blueprint = None

    def tearDown(self):
        pass

    def test_bytes_filter_ignores(self):
        f = renderers.bytes_filter
        self.assertEqual(1234.56, f({}, 1234.56))
        self.assertEqual(None, f({}, None))
        self.assertEqual("foo", f({}, "foo"))
        self.assertEqual(-2, f({}, -2))

    def test_bytes_filter(self):
        f = renderers.bytes_filter
        self.assertEqual("0", f({}, 0))
        self.assertEqual("999", f({}, 999))
        self.assertEqual('1<span class="secondary">,</span>234', f({}, 1234))
        self.assertEqual(
            '12<span class="secondary">,</span>345<span class="secondary">,</span>678',
            f({}, 12345678),
        )

    def test_style_background_bar_filter_ignores(self):
        f = renderers.style_background_bar_filter
        self.assertEqual("", f({}, "foo", 123))
        self.assertEqual("", f({}, 10, "foo"))

    def test_style_background_bar_filter(self):
        f = renderers.style_background_bar_filter
        expected = "background:linear-gradient(90deg, rgba(0,0,255,0.07) 8%, transparent 8%);"
        self.assertEqual(expected, f({}, 10, 123))

        expected = "background:linear-gradient(90deg, black 100%, transparent 100%);"
        self.assertEqual(expected, f({}, 200, 123, "black"))

    def test_sorted_filter_name(self):
        ctx = Mock()
        ctx.parent = {"sort": "name_asc"}
        a = {"display_name": "a"}
        b = {"name": "b"}
        c = {"display_name": "C"}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([a, b, c], actual)

        ctx.parent = {"sort": "name_desc"}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_sorted_filter_code(self):
        ctx = Mock()
        ctx.parent = {"sort": "code_asc"}
        a = {"type": "folder", "sub_folders": [], "files": []}
        b = {"type": "file", "symbols": [{"type": "function", "size": 200}]}
        c = {"type": "file", "symbols": [{"type": "function", "size": 300}]}
        actual = renderers.sorted_filter(ctx, [b, c, a])

        self.assertEqual([a, b, c], actual)

        ctx.parent = {"sort": "code_desc"}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_sorted_filter_vars(self):
        ctx = Mock()
        ctx.parent = {"sort": "vars_asc"}
        a = {"type": "folder", "sub_folders": [], "files": []}
        b = {"type": "file", "symbols": [{"type": "variable", "size": 200}]}
        c = {"type": "file", "symbols": [{"type": "variable", "size": 300}]}
        actual = renderers.sorted_filter(ctx, [b, c, a])

        self.assertEqual([a, b, c], actual)

        ctx.parent = {"sort": "vars_desc"}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_sorted_filter_stack(self):
        ctx = Mock()
        ctx.parent = {"sort": "stack_asc"}
        a = {"type": "folder", "sub_folders": [], "files": []}
        b = {"type": "file", "symbols": [{"type": "function", "stack_size": 200}]}
        c = {"type": "file", "symbols": [{"type": "function", "stack_size": 300}]}
        actual = renderers.sorted_filter(ctx, [b, c, a])

        self.assertEqual([a, b, c], actual)

        ctx.parent = {"sort": "stack_desc"}
        actual = renderers.sorted_filter(ctx, [b, c, a])
        self.assertEqual([c, b, a], actual)

    def test_col_sortable_filter_name(self):
        from flask import Flask

        app = Flask(__name__)
        # First test with foo=bar
        with app.test_request_context(query_string="foo=bar"):
            ctx = Mock()
            ctx.parent = {}
            expected = '<a href="http://localhost/?foo=bar&sort=name_asc" class="sortable">Name</a>'
            actual = renderers.col_sortable_filter(ctx, "Name", True)
            self.assertEqual(expected, actual)

        # Second test with sort=foo
        with app.test_request_context(query_string="sort=foo"):
            ctx = Mock()
            ctx.parent = {"sort": "name_asc"}
            expected = '<a href="http://localhost/?sort=name_desc" class="sortable sort_asc_alpha">Name</a>'
            actual = renderers.col_sortable_filter(ctx, "Name", True)
            self.assertEqual(expected, actual)

    def test_col_sortable_filter_stack(self):
        from flask import Flask

        app = Flask(__name__)
        # First test with foo=bar
        with app.test_request_context(query_string="foo=bar"):
            ctx = Mock()
            ctx.parent = {}
            expected = (
                '<a href="http://localhost/?foo=bar&sort=stack_asc" class="sortable">Stack</a>'
            )
            actual = renderers.col_sortable_filter(ctx, "Stack", True)
            self.assertEqual(expected, actual)

        # Second test with sort=foo
        with app.test_request_context(query_string="sort=foo"):
            ctx = Mock()
            ctx.parent = {"sort": "stack_asc"}
            expected = '<a href="http://localhost/?sort=stack_desc" class="sortable sort_asc_alpha">Stack</a>'
            actual = renderers.col_sortable_filter(ctx, "Stack", True)
            self.assertEqual(expected, actual)

    def test_url_for(self):
        from flask import Flask

        app = Flask(__name__)
        with app.test_request_context():
            c = Mock()
            c.root_folders = Mock(return_value=[])
            c.all_symbols = Mock(return_value=[])
            c.all_functions = Mock(return_value=[])
            c.all_variables = Mock(return_value=[])
            c = renderers.HTMLRenderer(c)

            from unittest.mock import patch

            with patch("puncover.renderers.url_for", return_value="/"):
                actual = c.url_for("/")
                self.assertEqual("/", actual)

                # preserves query parameters
                from flask import Flask

                app = Flask(__name__)
                # First test with no query string
                with app.test_request_context():
                    c = Mock()
                    c.root_folders = Mock(return_value=[])
                    c.all_symbols = Mock(return_value=[])
                    c.all_functions = Mock(return_value=[])
                    c.all_variables = Mock(return_value=[])
                    c = renderers.HTMLRenderer(c)

                    from unittest.mock import patch

                    with patch("puncover.renderers.url_for", return_value="/"):
                        actual = c.url_for("/")
                        self.assertEqual("/", actual)

                # Second test with foo=bar
                with app.test_request_context(query_string="foo=bar"):
                    c = Mock()
                    c.root_folders = Mock(return_value=[])
                    c.all_symbols = Mock(return_value=[])
                    c.all_functions = Mock(return_value=[])
                    c.all_variables = Mock(return_value=[])
                    c = renderers.HTMLRenderer(c)

                    from unittest.mock import patch

                    with patch("puncover.renderers.url_for", return_value="/"):
                        actual = c.url_for("/")
                        self.assertEqual("/?foo=bar", actual)
