import unittest
from unittest.mock import Mock

from puncover import collector, renderers


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

    def test_none_sum_empty_list(self):
        """Test that none_sum returns None for an empty list"""
        self.assertIsNone(renderers.none_sum([]))

    def test_none_sum_all_none(self):
        """Test that none_sum returns None when all values are None"""
        self.assertIsNone(renderers.none_sum([None, None, None]))

    def test_none_sum_some_none(self):
        """Test that none_sum ignores None values and sums the rest"""
        self.assertEqual(10, renderers.none_sum([None, 3, None, 7]))
        self.assertEqual(5, renderers.none_sum([5, None]))
        self.assertEqual(5, renderers.none_sum([None, 5]))

    def test_none_sum_no_none(self):
        """Test that none_sum works correctly when there are no None values"""
        self.assertEqual(15, renderers.none_sum([5, 10]))
        self.assertEqual(10, renderers.none_sum([1, 2, 3, 4]))

    def test_none_sum_single_value(self):
        """Test that none_sum works with a single value"""
        self.assertEqual(42, renderers.none_sum([42]))
        self.assertIsNone(renderers.none_sum([None]))

    def test_symbol_stack_size_filter_with_none_values(self):
        """Test that symbol_stack_size_filter handles directories with no stack data"""
        from flask import Flask

        app = Flask(__name__)
        with app.test_request_context():
            ctx = Mock()

            # Test folder with files that have no stack size
            folder = {
                collector.TYPE: collector.TYPE_FOLDER,
                collector.SUB_FOLDERS: [],
                collector.FILES: [
                    {
                        collector.TYPE: collector.TYPE_FILE,
                        collector.SYMBOLS: [
                            {
                                collector.TYPE: collector.TYPE_FUNCTION,
                                # No stack_size key - should be treated as None
                            }
                        ],
                    }
                ],
            }

            result = renderers.symbol_stack_size_filter(ctx, folder)
            # Should return None when all stack sizes are None
            self.assertIsNone(result)

    def test_symbol_stack_size_filter_with_stack_values(self):
        """Test that symbol_stack_size_filter correctly sums stack sizes"""
        from flask import Flask

        app = Flask(__name__)
        with app.test_request_context():
            ctx = Mock()

            # Test folder with files that have stack sizes
            folder = {
                collector.TYPE: collector.TYPE_FOLDER,
                collector.SUB_FOLDERS: [],
                collector.FILES: [
                    {
                        collector.TYPE: collector.TYPE_FILE,
                        collector.SYMBOLS: [
                            {collector.TYPE: collector.TYPE_FUNCTION, collector.STACK_SIZE: 100},
                            {collector.TYPE: collector.TYPE_FUNCTION, collector.STACK_SIZE: 200},
                        ],
                    }
                ],
            }

            result = renderers.symbol_stack_size_filter(ctx, folder)
            self.assertEqual(300, result)

    def test_symbol_stack_size_filter_mixed_stack_values(self):
        """Test symbol_stack_size_filter with mixed None and actual values"""
        from flask import Flask

        app = Flask(__name__)
        with app.test_request_context():
            ctx = Mock()

            # Test folder with mixed stack sizes and missing values
            folder = {
                collector.TYPE: collector.TYPE_FOLDER,
                collector.SUB_FOLDERS: [],
                collector.FILES: [
                    {
                        collector.TYPE: collector.TYPE_FILE,
                        collector.SYMBOLS: [
                            {collector.TYPE: collector.TYPE_FUNCTION, collector.STACK_SIZE: 150},
                            {
                                collector.TYPE: collector.TYPE_FUNCTION,
                                # No stack_size - should be treated as None
                            },
                        ],
                    },
                    {
                        collector.TYPE: collector.TYPE_FILE,
                        collector.SYMBOLS: [
                            {
                                collector.TYPE: collector.TYPE_VARIABLE,
                                # Variables don't have stack_size
                            }
                        ],
                    },
                ],
            }

            result = renderers.symbol_stack_size_filter(ctx, folder)
            self.assertEqual(150, result)

    def test_sorted_filter_stack_with_none_values(self):
        """Test that sorting by stack size works correctly with None values (PR #128)"""
        ctx = Mock()
        ctx.parent = {"sort": "stack_asc"}

        # Folder with no stack data (should be treated as 0/None)
        a = {collector.TYPE: collector.TYPE_FOLDER, collector.SUB_FOLDERS: [], collector.FILES: []}

        # File with function that has no stack_size
        b = {
            collector.TYPE: collector.TYPE_FILE,
            collector.SYMBOLS: [
                {
                    collector.TYPE: collector.TYPE_FUNCTION,
                    # No stack_size key
                }
            ],
        }

        # File with function that has stack_size
        c = {
            collector.TYPE: collector.TYPE_FILE,
            collector.SYMBOLS: [
                {collector.TYPE: collector.TYPE_FUNCTION, collector.STACK_SIZE: 300}
            ],
        }

        # Should not crash when sorting - this was the bug in PR #128
        actual = renderers.sorted_filter(ctx, [c, b, a])

        # Items with no stack size (converted to 0) should come first in ascending order,
        # then items with stack size. The order of a and b may vary since both are 0.
        # The key point is that c (with stack_size=300) comes last and no crash occurs.
        self.assertEqual(c, actual[2])
        self.assertIn(a, actual[:2])
        self.assertIn(b, actual[:2])
