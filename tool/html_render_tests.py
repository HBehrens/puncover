import unittest
import renderers

class TestHTMLRenderer(unittest.TestCase):

    def test_assembly_filter_simple_link(self):
        line = "   b8:	f000 f8de 	bleq	278 &lt;__aeabi_dmul+0x1dc&gt;"
        actual = renderers.assembly_filter(None, line)
        self.assertIn("href", actual)