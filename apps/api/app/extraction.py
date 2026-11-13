import re
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_PAGES = 20
MAX_PAGE_CHARS = 12_000
CHUNK_CHARS = 2_400

SpecKey = Literal[
    "product_category", "operating_frequency", "depth_rating", "maximum_range",
    "horizontal_beam_width", "vertical_beam_width", "interface", "supply_voltage",
]
LABELS: dict[SpecKey, str] = {
    "product_category": "Category",
    "operating_frequency": "Operating frequency",
    "depth_rating": "Depth rating",
    "maximum_range": "Maximum range",
    "horizontal_beam_width": "Horizontal beam width",
    "vertical_beam_width": "Vertical beam width",
    "interface": "Interface",
    "supply_voltage": "Supply voltage",
}
ALIASES = {label.casefold(): key for key, label in LABELS.items()} | {
    "product category": "product_category",
    "frequency": "operating_frequency",
    "maximum operating depth": "depth_rating",
    "max range": "maximum_range",
    "data interface": "interface",
    "input voltage": "supply_voltage",
}


class DocumentError(ValueError):
    """A safe, user-facing document validation error."""


@dataclass(frozen=True)
class Passage:
    page: int
    part: int
    text: str

    @property
    def locator(self) -> str:
        return f"Page {self.page} · Section {self.part}"


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage: int
    key: SpecKey
    value: str
    quote: str


class ProposalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[Proposal]


def read_pdf(data: bytes) -> tuple[int, list[Passage]]:
    if not data.startswith(b"%PDF-"):
        raise DocumentError("Upload a PDF file with a valid PDF header.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError("PDFs must be 8 MiB or smaller.")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise DocumentError("Encrypted PDFs are unsupported.")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PAGES:
            raise DocumentError("PDFs must contain 1–20 pages.")
        passages: list[Passage] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text().replace("\x00", "").strip()
            if len(text) > MAX_PAGE_CHARS:
                raise DocumentError("A PDF page exceeds the extracted-text limit.")
            remaining = text
            part = 1
            while remaining:
                end = len(remaining)
                if end > CHUNK_CHARS:
                    end = remaining.rfind("\n", 0, CHUNK_CHARS + 1)
                    end = end if end > 0 else CHUNK_CHARS
                section = remaining[:end].strip()
                if section:
                    passages.append(Passage(page_number, part, section))
                remaining = remaining[end:].lstrip()
                part += 1
    except DocumentError:
        raise
    except Exception as error:
        raise DocumentError("The PDF could not be parsed. Try exporting it as a text PDF.") from error
    if not passages:
        raise DocumentError("No selectable text found. OCR is required for scanned PDFs.")
    return page_count, passages


def extract_labeled_lines(passages: list[Passage]) -> list[Proposal]:
    proposals = []
    for index, passage in enumerate(passages):
        for line in passage.text.splitlines():
            quote = line.strip()
            label, separator, value = quote.partition(":")
            key = ALIASES.get(label.strip().casefold())
            if separator and key and value.strip():
                proposals.append(Proposal(passage=index, key=key, value=value.strip(), quote=quote))
    return proposals


def supports_value(text: str, quote: str, value: str, key: str) -> bool:
    if not (0 < len(quote) <= 600 and 0 < len(value) <= 160 and quote in text):
        return False
    if value != value.strip() or not any(char.isalnum() for char in value):
        return False
    if re.search(r"(?<![\w.+-])" + re.escape(value) + r"(?![\w+-]|[.,]\d)", quote) is None:
        return False
    # A recognized labeled line supplies its complete value, including qualifiers.
    matching_lines = [line for line in text.splitlines() if quote in line or (line in quote and value in line)]
    for line in matching_lines:
        label, separator, remainder = line.partition(":")
        labeled_key = ALIASES.get(label.strip().casefold())
        if separator and labeled_key and (key != labeled_key or value != remainder.strip()):
            return False
    return True


def grounded_proposals(passages: list[Passage], proposals: list[Proposal]) -> list[Proposal]:
    grounded = {}
    for proposal in proposals:
        if not 0 <= proposal.passage < len(passages):
            continue
        if supports_value(passages[proposal.passage].text, proposal.quote, proposal.value, proposal.key):
            key = (proposal.passage, proposal.key, proposal.value)
            grounded.setdefault(key, proposal)
    if len(grounded) > 300:
        raise DocumentError("The PDF contains too many specification candidates.")
    return list(grounded.values())
