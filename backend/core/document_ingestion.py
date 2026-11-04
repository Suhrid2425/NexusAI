
import csv
import io
import math
import zipfile
from pathlib import Path
import zlib
from bs4 import BeautifulSoup
from docx import Document as WordDocument
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".html",
    ".htm",
}

MAX_ARCHIVE_ENTRIES = 5000
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_COMPRESSION_RATIO = 100


def _validate_office_archive(raw_bytes, extension):
    """Reject malformed or excessively compressed Office archives."""
    required_files = {
        ".docx": "word/document.xml",
        ".pptx": "ppt/presentation.xml",
        ".xlsx": "xl/workbook.xml",
    }

    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            entries = archive.infolist()

            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise ValueError(
                    "The Office document contains too many archive entries."
                )

            total_uncompressed = 0

            for entry in entries:
                if entry.flag_bits & 0x1:
                    raise ValueError(
                        "Encrypted Office documents are not supported."
                    )

                if entry.file_size < 0 or entry.compress_size < 0:
                    raise ValueError(
                        "The Office document contains invalid archive metadata."
                    )

                total_uncompressed += entry.file_size

                if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
                    raise ValueError(
                        "The Office document expands beyond the allowed size."
                    )

                if entry.file_size > 0 and entry.compress_size == 0:
                    raise ValueError(
                        "The Office document has an invalid compression ratio."
                    )

                if entry.compress_size > 0:
                    ratio = entry.file_size / entry.compress_size

                    if (
                        not math.isfinite(ratio)
                        or ratio > MAX_COMPRESSION_RATIO
                    ):
                        raise ValueError(
                            "The Office document is excessively compressed."
                        )

            if required_files[extension] not in archive.namelist():
                raise ValueError(
                    "The uploaded file is not a valid Office document."
                )

            bad_file = archive.testzip()

            if bad_file is not None:
                raise ValueError(
                    "The Office document archive is corrupted."
                )

    except (
        zipfile.BadZipFile,
        EOFError,
        RuntimeError,
        NotImplementedError,
        zlib.error,
    ) as exc:
        raise ValueError(
            "The uploaded file is not a valid or readable Office document."
        ) from exc

def _decode_text(raw_bytes):
    """Decode text using common encodings."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError("Unsupported text-file encoding.")


def extract_document_text(file_field):
    """Extract text from a supported Django FileField."""
    extension = Path(file_field.name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension or 'unknown'}."
        )

    file_field.open("rb")
    try:
        raw_bytes = file_field.read()
    finally:
        file_field.close()

    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")

    # Validate Office archives before passing them to document parsers.
    if extension in {".docx", ".pptx", ".xlsx"}:
        _validate_office_archive(raw_bytes, extension)

    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(raw_bytes))

        if reader.is_encrypted:
            raise ValueError(
                "Password-protected PDFs are not supported."
            )

        text = "\n".join(
            (page.extract_text() or "").strip()
            for page in reader.pages
        )

    elif extension == ".docx":
        document = WordDocument(io.BytesIO(raw_bytes))
        parts = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                parts.append(paragraph.text.strip())

        for table in document.tables:
            for row in table.rows:
                parts.append(
                    " | ".join(cell.text.strip() for cell in row.cells)
                )

        text = "\n".join(parts)

    elif extension == ".pptx":
        presentation = Presentation(io.BytesIO(raw_bytes))
        parts = []

        for number, slide in enumerate(presentation.slides, start=1):
            parts.append(f"Slide {number}")

            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    value = shape.text.strip()
                    if value:
                        parts.append(value)

                if getattr(shape, "has_table", False):
                    for row in shape.table.rows:
                        parts.append(
                            " | ".join(
                                cell.text.strip()
                                for cell in row.cells
                            )
                        )

        text = "\n".join(parts)

    elif extension == ".xlsx":
        workbook = load_workbook(
            io.BytesIO(raw_bytes),
            read_only=True,
            data_only=True,
        )
        parts = []

        try:
            for sheet in workbook.worksheets:
                parts.append(f"Sheet: {sheet.title}")

                for row in sheet.iter_rows(values_only=True):
                    values = [
                        str(value).strip()
                        for value in row
                        if value is not None and str(value).strip()
                    ]

                    if values:
                        parts.append(" | ".join(values))
        finally:
            workbook.close()

        text = "\n".join(parts)

    elif extension == ".csv":
        rows = csv.reader(
            io.StringIO(_decode_text(raw_bytes))
        )
        text = "\n".join(
            " | ".join(cell.strip() for cell in row)
            for row in rows
            if any(cell.strip() for cell in row)
        )

    elif extension in {".html", ".htm"}:
        soup = BeautifulSoup(
            _decode_text(raw_bytes),
            "html.parser",
        )

        for element in soup(
            ["script", "style", "noscript", "svg"]
        ):
            element.decompose()

        text = soup.get_text(separator="\n", strip=True)

    else:
        # Plain text and Markdown.
        text = _decode_text(raw_bytes)

    # Normalize whitespace and remove blank lines.
    text = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ).strip()

    if not text:
        raise ValueError("No extractable text was found in the file.")

    return text
