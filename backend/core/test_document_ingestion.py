
import io
import zipfile
import zlib
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.document_ingestion import (
    _validate_office_archive,
    extract_document_text,
)


class OfficeArchiveValidationTests(SimpleTestCase):
    def make_archive(self, filename, entries):
        buffer = io.BytesIO()

        with zipfile.ZipFile(
            buffer,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for name, content in entries.items():
                archive.writestr(name, content)

        return SimpleUploadedFile(
            filename,
            buffer.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument"
            ),
        )

    def test_rejects_invalid_docx_archive(self):
        uploaded = SimpleUploadedFile(
            "broken.docx",
            b"not a zip archive",
        )

        with self.assertRaises(ValueError):
            extract_document_text(uploaded)

    def test_rejects_archive_missing_required_document(self):
        archive = self.make_archive(
            "invalid.docx",
            {"other.xml": "<root />"},
        )

        with self.assertRaises(ValueError):
            extract_document_text(archive)

    def test_accepts_archive_with_required_document(self):
        archive = self.make_archive(
            "minimal.docx",
            {
                "[Content_Types].xml": "<Types />",
                "word/document.xml": "<document />",
            },
        )

        # Validate the archive only; this is not a complete DOCX file.
        _validate_office_archive(
            archive.read(),
            ".docx",
        )

    def test_rejects_too_many_archive_entries(self):
        entries = {
            f"file_{number}.xml": "x"
            for number in range(5001)
        }

        archive = self.make_archive("many.docx", entries)

        with self.assertRaises(ValueError):
            _validate_office_archive(
                archive.read(),
                ".docx",
            )

    def test_converts_decompression_error_to_value_error(self):
        buffer = io.BytesIO()

        with zipfile.ZipFile(
            buffer,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                "word/document.xml",
                "<document>Example</document>",
            )

        with patch(
            "core.document_ingestion.zipfile.ZipFile.testzip",
            side_effect=zlib.error("Simulated decompression failure"),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "valid or readable Office document",
            ):
                _validate_office_archive(
                    buffer.getvalue(),
                    ".docx",
                )
