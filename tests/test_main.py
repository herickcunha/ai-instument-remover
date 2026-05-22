import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# Mock customtkinter before importing main
import sys


class MockBaseWidget:
    def __init__(self, *a, **kw): pass
    def __getattr__(self, name):
        return lambda *a, **kw: None


class MockCTk(MockBaseWidget):
    pass
    def title(self, *a): pass
    def geometry(self, *a): pass
    def minsize(self, *a): pass
    def grid_columnconfigure(self, *a, **kw): pass
    def grid_rowconfigure(self, *a, **kw): pass
    def protocol(self, *a, **kw): pass
    def destroy(self): pass
    def after(self, ms, func, *a):
        return None
    def after_cancel(self, _id): pass
    def update_idletasks(self): pass
    def winfo_toplevel(self): return self
    def attributes(self, *a, **kw): pass
    def wm_overrideredirect(self, *a): pass
    def wm_geometry(self, *a): pass


class MockFont:
    def __init__(self, *a, **kw): pass


class MockVar:
    def __init__(self, *a, **kw): self.value = kw.get("value")
    def get(self): return self.value
    def set(self, v): self.value = v


mock_ctk = MagicMock()
mock_ctk.CTk = MockCTk
mock_ctk.CTkFrame = MockBaseWidget
mock_ctk.CTkLabel = MockBaseWidget
mock_ctk.CTkEntry = MockBaseWidget
mock_ctk.CTkButton = MockBaseWidget
mock_ctk.CTkCheckBox = MockBaseWidget
mock_ctk.CTkSlider = MockBaseWidget
mock_ctk.CTkProgressBar = MockBaseWidget
mock_ctk.CTkSegmentedButton = MockBaseWidget
mock_ctk.CTkFont = MockFont
mock_ctk.StringVar = MockVar
mock_ctk.IntVar = MockVar
mock_ctk.BooleanVar = MockVar
mock_ctk.set_appearance_mode = MagicMock()
mock_ctk.set_default_color_theme = MagicMock()
mock_ctk.get_appearance_mode = MagicMock(return_value="Dark")

sys.modules["customtkinter"] = mock_ctk

from main import App


class TestConfigPersistence:
    def test_load_config_missing(self):
        with patch("main.CONFIG_PATH", Path(tempfile.mktemp(suffix=".json"))):
            app = App()
            app.config = {}
            result = app._load_config()
            assert result == {}

    def test_load_config_valid(self):
        data = {"dest_dir": "C:\\test", "detect_bpm": True}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        try:
            with patch("main.CONFIG_PATH", Path(path)):
                app = App()
                app.config = {}
                result = app._load_config()
                assert result == data
        finally:
            os.unlink(path)

    def test_load_config_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            path = f.name

        try:
            with patch("main.CONFIG_PATH", Path(path)):
                app = App()
                app.config = {}
                result = app._load_config()
                assert result == {}
        finally:
            os.unlink(path)

    def test_save_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            with patch("main.CONFIG_PATH", Path(path)):
                app = App()
                app.config = {"dest_dir": "C:\\test", "detect_bpm": True}
                app._save_config()

                with open(path, "r") as f:
                    data = json.load(f)
                assert data == app.config
        finally:
            os.unlink(path)


class TestSourceModeChange:
    def test_switch_to_local(self):
        app = App()
        app.source_mode = MagicMock()
        app.url_entry = MagicMock()
        app.local_frame = MagicMock()

        app._on_source_change("Local File")
        assert app.source_mode.set.call_args[0][0] == "local"
        app.url_entry.grid_remove.assert_called_once()
        app.local_frame.grid.assert_called_once()

    def test_switch_to_youtube(self):
        app = App()
        app.source_mode = MagicMock()
        app.url_entry = MagicMock()
        app.local_frame = MagicMock()

        app._on_source_change("YouTube")
        assert app.source_mode.set.call_args[0][0] == "youtube"
        app.url_entry.grid.assert_called_once()
        app.local_frame.grid_remove.assert_called_once()


class TestShiftChange:
    def test_update_label(self):
        app = App()
        app.shifts_label = MagicMock()

        app._on_shift_change(5.0)
        app.shifts_label.configure.assert_called_once_with(text="Shifts: 5")

    def test_update_label_float(self):
        app = App()
        app.shifts_label = MagicMock()

        app._on_shift_change(3.7)
        app.shifts_label.configure.assert_called_once_with(text="Shifts: 3")
