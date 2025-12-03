import unittest
from unittest.mock import MagicMock, patch

from puncover.puncover import main


class TestArguments(unittest.TestCase):
    """
    Test that critical command-line arguments maintain their exact names.
    These arguments are used by external tools (e.g., Zephyr build system)
    and must not be changed to maintain backward compatibility.
    """

    def _create_mock_environment(self):
        """Create mocked environment for testing argument parsing."""
        mock_builder = MagicMock()
        mock_builder.collector = MagicMock()

        patches = [
            patch("puncover.puncover.create_builder", return_value=mock_builder),
            patch("puncover.puncover.renderers.register_jinja_filters"),
            patch("puncover.puncover.renderers.register_urls"),
            patch("puncover.puncover.app.run"),
            patch("puncover.puncover.is_port_in_use", return_value=False),
            patch(
                "puncover.puncover.get_arm_tools_prefix_path",
                return_value="/usr/bin/arm-none-eabi-",
            ),
            patch("os.path.exists", return_value=True),
            # disable delay in this test; this also disables open_browser
            patch("puncover.puncover.Timer"),
        ]

        return patches

    def test_gcc_tools_base_underscore_format(self):
        """Test that --gcc_tools_base argument works (underscore format)."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import create_builder

                main()
                # Verify create_builder was called with the gcc_tools_base argument
                create_builder.assert_called_once()
                call_args = create_builder.call_args
                self.assertEqual(call_args[0][0], "/path/to/gcc")
            finally:
                for p in patches:
                    p.stop()

    def test_gcc_tools_base_hyphen_format(self):
        """Test that --gcc-tools-base argument works (hyphen format)."""
        test_args = [
            "puncover",
            "--gcc-tools-base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import create_builder

                main()
                # Verify create_builder was called with the gcc_tools_base argument
                create_builder.assert_called_once()
                call_args = create_builder.call_args
                self.assertEqual(call_args[0][0], "/path/to/gcc")
            finally:
                for p in patches:
                    p.stop()

    def test_elf_file_underscore_format(self):
        """Test that --elf_file argument works (underscore format)."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/kernel.elf",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import create_builder

                main()
                # Verify create_builder was called with the elf_file argument
                create_builder.assert_called_once()
                call_args = create_builder.call_args
                self.assertEqual(call_args[1]["elf_file"], "/path/to/kernel.elf")
            finally:
                for p in patches:
                    p.stop()

    def test_src_root_underscore_format(self):
        """Test that --src_root argument works (underscore format)."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
            "--src_root",
            "/path/to/sources",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import create_builder

                main()
                # Verify create_builder was called with the src_root argument
                create_builder.assert_called_once()
                call_args = create_builder.call_args
                self.assertEqual(call_args[1]["src_root"], "/path/to/sources")
            finally:
                for p in patches:
                    p.stop()

    def test_src_root_hyphen_format(self):
        """Test that --src-root argument works (hyphen format)."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
            "--src-root",
            "/path/to/sources",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import create_builder

                main()
                # Verify create_builder was called with the src_root argument
                create_builder.assert_called_once()
                call_args = create_builder.call_args
                self.assertEqual(call_args[1]["src_root"], "/path/to/sources")
            finally:
                for p in patches:
                    p.stop()

    def test_build_dir_underscore_format(self):
        """Test that --build_dir argument works (underscore format)."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
            "--build_dir",
            "/path/to/build",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import create_builder

                main()
                # Verify create_builder was called with the su_dir (build_dir) argument
                create_builder.assert_called_once()
                call_args = create_builder.call_args
                self.assertEqual(call_args[1]["su_dir"], "/path/to/build")
            finally:
                for p in patches:
                    p.stop()

    def test_build_dir_hyphen_format(self):
        """Test that --build-dir argument works (hyphen format)."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
            "--build-dir",
            "/path/to/build",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import create_builder

                main()
                # Verify create_builder was called with the su_dir (build_dir) argument
                create_builder.assert_called_once()
                call_args = create_builder.call_args
                self.assertEqual(call_args[1]["su_dir"], "/path/to/build")
            finally:
                for p in patches:
                    p.stop()

    def test_host_argument(self):
        """Test that --host argument works."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
            "--host",
            "0.0.0.0",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import app

                main()
                # Verify app.run was called with the host argument
                app.run.assert_called_once()
                call_kwargs = app.run.call_args[1]
                self.assertEqual(call_kwargs["host"], "0.0.0.0")
            finally:
                for p in patches:
                    p.stop()

    def test_port_argument(self):
        """Test that --port argument works."""
        test_args = [
            "puncover",
            "--gcc_tools_base",
            "/path/to/gcc",
            "--elf_file",
            "/path/to/file.elf",
            "--port",
            "8080",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import app

                main()
                # Verify app.run was called with the port argument
                app.run.assert_called_once()
                call_kwargs = app.run.call_args[1]
                self.assertEqual(call_kwargs["port"], 8080)
            finally:
                for p in patches:
                    p.stop()

    def test_all_critical_arguments_together(self):
        """
        Test all critical arguments together as they would be used by Zephyr build system.

        This test ensures backward compatibility with external tools that depend on these
        exact argument names.
        """
        test_args = [
            "puncover",
            "--elf_file",
            "/build/zephyr/zephyr.elf",
            "--gcc-tools-base",
            "/usr/bin/arm-zephyr-eabi-",
            "--src_root",
            "/zephyr",
            "--build_dir",
            "/build",
            "--host",
            "0.0.0.0",
            "--port",
            "5000",
        ]

        patches = self._create_mock_environment()

        with patch("sys.argv", test_args):
            for p in patches:
                p.start()

            try:
                from puncover.puncover import app, create_builder

                main()

                # Verify all arguments were passed correctly
                create_builder.assert_called_once()
                call_args = create_builder.call_args

                # Check create_builder arguments
                self.assertEqual(call_args[0][0], "/usr/bin/arm-zephyr-eabi-")  # gcc_base_filename
                self.assertEqual(call_args[1]["elf_file"], "/build/zephyr/zephyr.elf")
                self.assertEqual(call_args[1]["src_root"], "/zephyr")
                self.assertEqual(call_args[1]["su_dir"], "/build")

                # Check app.run arguments
                app.run.assert_called_once()
                run_kwargs = app.run.call_args[1]
                self.assertEqual(run_kwargs["host"], "0.0.0.0")
                self.assertEqual(run_kwargs["port"], 5000)
            finally:
                for p in patches:
                    p.stop()


if __name__ == "__main__":
    unittest.main()
