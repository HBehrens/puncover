import unittest
from puncover import renderers


class TestRenderer(unittest.TestCase):

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
