import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import mutagen

from processor import (
    sanitize_filename,
    sanitize_folder_name,
    read_metadata,
    cleanup_temp,
)


class TestSanitizeFilename:
    def test_basic(self):
        assert sanitize_filename("Hello World") == "Hello World"

    def test_special_chars(self):
        assert sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_empty(self):
        assert sanitize_filename("") == "audio"

    def test_dots(self):
        assert sanitize_filename("  . ") == "audio"

    def test_trailing_spaces(self):
        assert sanitize_filename("  file  ") == "file"


class TestSanitizeFolderName:
    def test_basic(self):
        assert sanitize_folder_name("My Artist") == "My Artist"

    def test_special_chars(self):
        assert sanitize_folder_name("Rock / Metal") == "Rock _ Metal"

    def test_empty(self):
        assert sanitize_folder_name("") == "Unknown"

    def test_whitespace(self):
        assert sanitize_folder_name("   . ") == "Unknown"


class TestReadMetadata:
    def _create_mp3_with_tags(self, path, artist, album):
        from mutagen.id3 import ID3, TPE1, TALB, TT2

        audio = mutagen.File(path, easy=True)
        if audio is None:
            audio = mutagen.File(path)
        if audio is None:
            raise RuntimeError("Could not create test MP3")

        try:
            tags = ID3(path)
        except Exception:
            tags = ID3()

        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TALB(encoding=3, text=album))
        tags.save(path)

    def test_mp3_with_tags(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name
            f.write(b"\x00" * 1024)

        try:
            from mutagen.id3 import ID3, TPE1, TALB

            try:
                tags = ID3(path)
            except Exception:
                tags = ID3()

            tags.add(TPE1(encoding=3, text=["Test Artist"]))
            tags.add(TALB(encoding=3, text=["Test Album"]))
            tags.save(path)

            artist, album = read_metadata(path)
            assert artist == "Test Artist"
            assert album == "Test Album"
        finally:
            os.unlink(path)

    def test_mp3_no_tags(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name
            f.write(b"\x00" * 2048)

        try:
            artist, album = read_metadata(path)
            assert artist == "Unknown Artist"
            assert album == "Unknown Album"
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        artist, album = read_metadata("nonexistent.mp3")
        assert artist == "Unknown Artist"
        assert album == "Unknown Album"

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
            f.write(b"hello")

        try:
            artist, album = read_metadata(path)
            assert artist == "Unknown Artist"
            assert album == "Unknown Album"
        finally:
            os.unlink(path)

    def test_flac_with_tags(self):
        path = os.path.join(tempfile.mkdtemp(), "test.flac")
        try:
            import subprocess
            result = subprocess.run(
                [shutil.which("ffmpeg") or "ffmpeg", "-y", "-f", "lavfi",
                 "-i", "anullsrc=r=44100:cl=mono", "-t", "0.1",
                 "-metadata", "artist=Flac Artist",
                 "-metadata", "album=Flac Album",
                 path],
                capture_output=True, timeout=30,
            )
            if result.returncode != 0:
                pytest.skip("ffmpeg not available for FLAC creation")

            artist, album = read_metadata(path)
            assert artist == "Flac Artist"
            assert album == "Flac Album"
        finally:
            if os.path.exists(path):
                os.unlink(path)
            os.rmdir(os.path.dirname(path))

    def test_flac_no_tags(self):
        path = os.path.join(tempfile.mkdtemp(), "test.flac")
        try:
            import subprocess
            result = subprocess.run(
                [shutil.which("ffmpeg") or "ffmpeg", "-y", "-f", "lavfi",
                 "-i", "anullsrc=r=44100:cl=mono", "-t", "0.1", path],
                capture_output=True, timeout=30,
            )
            if result.returncode != 0:
                pytest.skip("ffmpeg not available for FLAC creation")

            artist, album = read_metadata(path)
            assert artist == "Unknown Artist"
            assert album == "Unknown Album"
        finally:
            if os.path.exists(path):
                os.unlink(path)
            os.rmdir(os.path.dirname(path))


class TestCleanupTemp:
    def test_cleanup_existing(self):
        with tempfile.TemporaryDirectory() as d:
            sub = Path(d) / "subdir"
            sub.mkdir()
            (sub / "file.txt").write_text("test")

            cleanup_temp(Path(d))
            assert not Path(d).exists()

    def test_cleanup_nonexistent(self):
        cleanup_temp(Path("/nonexistent/path"))
