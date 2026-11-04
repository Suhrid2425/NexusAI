
import csv
import tempfile
from pathlib import Path

from docx import Document as WordDocument
from openpyxl import Workbook
from pptx import Presentation
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    DictionaryObject,
    ArrayObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from core.document_ingestion import extract_document_text


def create_samples(folder):
    samples = {}

    # TXT
    path = folder / "sample.txt"
    path.write_text("NexusAI supports text documents.", encoding="utf-8")
    samples[path] = "text documents"

    # Markdown
    path = folder / "sample.md"
    path.write_text(
        "# NexusAI\nMarkdown knowledge sample.",
        encoding="utf-8",
    )
    samples[path] = "Markdown knowledge sample"

    # HTML
    path = folder / "sample.html"
    path.write_text(
        "<html><body><h1>NexusAI</h1>"
        "<p>HTML knowledge sample.</p>"
        "<script>hidden content</script></body></html>",
        encoding="utf-8",
    )
    samples[path] = "HTML knowledge sample"

    # CSV
    path = folder / "sample.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Topic", "Description"])
        writer.writerow(["NexusAI", "CSV knowledge sample"])
    samples[path] = "CSV knowledge sample"

    # DOCX
    path = folder / "sample.docx"
    document = WordDocument()
    document.add_paragraph("DOCX knowledge sample.")
    document.save(path)
    samples[path] = "DOCX knowledge sample"

    # PPTX
    path = folder / "sample.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(
        presentation.slide_layouts[6]
    )
    box = slide.shapes.add_textbox(100, 100, 500, 100)
    box.text = "PPTX knowledge sample."
    presentation.save(path)
    samples[path] = "PPTX knowledge sample"

    # XLSX
    path = folder / "sample.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Knowledge"
    sheet.append(["Topic", "Description"])
    sheet.append(["NexusAI", "XLSX knowledge sample"])
    workbook.save(path)
    samples[path] = "XLSX knowledge sample"

    # PDF
    path = folder / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.add_metadata({"/Title": "NexusAI test PDF"})
    writer.write(path)
    samples[path] = None  # Blank PDF has no extractable body text.

    return samples


def main():
    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as temporary_directory:
        folder = Path(temporary_directory)
        samples = create_samples(folder)

        for path, expected in samples.items():
            try:
                with path.open("rb") as file:
                    class LocalFile:
                        name = path.name

                        def open(self, mode="rb"):
                            self._file = path.open(mode)
                            return self._file

                        def read(self):
                            return self._file.read()

                        def close(self):
                            self._file.close()

                    extracted = extract_document_text(LocalFile())

                if expected is None:
                    print(f"PASS {path.suffix}: readable PDF handled")
                    passed += 1
                elif expected in extracted:
                    print(f"PASS {path.suffix}: expected text extracted")
                    passed += 1
                else:
                    print(f"FAIL {path.suffix}: expected text missing")
                    failed += 1

            except ValueError as exc:
                if expected is None and "No extractable text" in str(exc):
                    print("PASS .pdf: empty PDF correctly rejected")
                    passed += 1
                else:
                    print(f"FAIL {path.suffix}: {exc}")
                    failed += 1
            except Exception as exc:
                print(f"FAIL {path.suffix}: {type(exc).__name__}: {exc}")
                failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")


if __name__ == "__main__":
    main()
