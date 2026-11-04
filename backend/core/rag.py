
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Document


SECTION_LEVELS = {"easy", "medium", "hard"}


def _clean_lines(text):
    """Normalize extracted text and repair split numbered list items."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    cleaned = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # PDF extraction sometimes separates "1." from its title.
        if (
            re.fullmatch(r"\d{1,4}[.)]", line)
            and i + 1 < len(lines)
        ):
            cleaned.append(f"{line} {lines[i + 1]}")
            i += 2
            continue

        cleaned.append(line)
        i += 1

    return cleaned


def _is_heading(line):
    """Recognize common standalone headings."""

    line = line.strip()

    if not line or len(line) > 100:
        return False

    if re.match(r"^#{1,6}\s+\S", line):
        return True

    if line.endswith(":"):
        return True

    return False


def split_into_chunks(text, chunk_size=900, overlap=150):
    """
    Split text into bounded chunks while preserving section context.

    When a section is too large, split its content into multiple chunks
    and repeat the document title and section heading for context.
    """

    if not text or not text.strip():
        return []

    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than zero.")

    overlap = max(0, min(overlap, chunk_size - 1))

    lines = _clean_lines(text)

    if not lines:
        return []

    # Preserve a short, all-uppercase first line as the document title.
    document_title = None
    first_line = lines[0]

    if (
        len(first_line) <= 120
        and first_line == first_line.upper()
        and any(char.isalpha() for char in first_line)
        and not _is_heading(first_line)
    ):
        document_title = first_line
        lines = lines[1:]

    chunks = []
    section_headings = []
    content_lines = []

    def flush_content():
        nonlocal content_lines

        if not content_lines:
            return

        # Include document title and current section headings.
        context_headings = []

        if document_title:
            context_headings.append(document_title)

        context_headings.extend(section_headings)

        heading = "\n".join(context_headings).strip()
        heading_prefix = f"{heading}\n" if heading else ""

        # Reserve space for the section heading in each chunk.
        available = chunk_size - len(heading_prefix)

        if available < 1:
            heading_prefix = heading[:chunk_size - 1] + "\n"
            available = chunk_size - len(heading_prefix)

        current = ""

        for line in content_lines:

            # An individual line can be longer than the available space.
            if len(line) > available:
                if current:
                    chunks.append(
                        (heading_prefix + current).strip()
                    )
                    current = ""

                start = 0

                while start < len(line):
                    part = line[start:start + available]

                    chunks.append(
                        (heading_prefix + part).strip()
                    )

                    if start + available >= len(line):
                        break

                    step = max(1, available - overlap)
                    start += step

                continue

            candidate = (
                f"{current}\n{line}".strip()
                if current
                else line
            )

            if len(candidate) <= available:
                current = candidate

            else:
                if current:
                    chunks.append(
                        (heading_prefix + current).strip()
                    )

                # Carry a small amount of prior content into the next
                # chunk, without crossing a section boundary.
                prefix = (
                    current[-overlap:].strip()
                    if overlap and current
                    else ""
                )

                candidate = (
                    f"{prefix}\n{line}".strip()
                    if prefix
                    else line
                )

                if len(candidate) <= available:
                    current = candidate
                else:
                    current = line

        if current:
            chunks.append(
                (heading_prefix + current).strip()
            )

        content_lines = []

    for line in lines:

        if _is_heading(line):
            flush_content()

            normalized_heading = re.sub(
                r"^#{1,6}\s+",
                "",
                line,
            ).strip()

            # Easy, Medium and Hard are subheadings.
            # Keep the parent section and replace its previous difficulty.
            if normalized_heading.rstrip(":").lower() in SECTION_LEVELS:

                if section_headings:
                    if (
                        section_headings[-1]
                        .rstrip(":")
                        .lower()
                        in SECTION_LEVELS
                    ):
                        section_headings.pop()

                    section_headings.append(normalized_heading)

                else:
                    section_headings = [normalized_heading]

            else:
                # A new main heading begins a new section.
                section_headings = [normalized_heading]

            continue

        content_lines.append(line)

    flush_content()

    return [
        chunk
        for chunk in chunks
        if chunk.strip()
    ]


def retrieve_relevant_chunks(organization_id, question, top_k=4):
    """Retrieve keyword-relevant passages from completed documents."""

    if (
        not isinstance(question, str)
        or not question.strip()
        or top_k < 1
    ):
        return []

    documents = Document.objects.filter(
        organization_id=organization_id,
        status=Document.Status.COMPLETED,
    ).exclude(
        extracted_text=""
    ).order_by("id")

    passages = []

    for document in documents:
        chunks = split_into_chunks(
            document.extracted_text or ""
        )

        for index, chunk in enumerate(chunks):
            passages.append({
                "document_id": document.id,
                "title": document.title,
                "chunk_index": index,
                "text": chunk,
            })

    if not passages:
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )

    try:
        matrix = vectorizer.fit_transform(
            [passage["text"] for passage in passages]
            + [question.strip()]
        )

    except ValueError:
        return []

    document_vectors = matrix[:-1]
    question_vector = matrix[-1]

    scores = cosine_similarity(
        question_vector,
        document_vectors,
    ).ravel()

    ranked_indices = scores.argsort()[::-1]
    results = []

    for index in ranked_indices:
        score = float(scores[index])

        if score <= 0:
            continue

        results.append({
            **passages[index],
            "relevance_score": round(score, 4),
        })

        if len(results) >= top_k:
            break

    return results
