"""Generate the checked-in synthetic fixtures. Run from any directory."""

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


FIXTURES = {
    "fixture-s2.pdf": [
        ["SYNTHETIC TEST DATA - NOT A COMMERCIAL PRODUCT", "FIXTURE-S2",
         "Operating frequency: 900 kHz", "Depth rating: 300 m",
         "Example use: submerged infrastructure inspection."],
        ["SYNTHETIC TEST DATA - NOT A COMMERCIAL PRODUCT", "Interface: Ethernet",
         "Supply voltage: 24 V DC", "Search anchor: fixture-beacon-alpha."],
    ],
    "fixture-s4.pdf": [
        ["SYNTHETIC TEST DATA - NOT A COMMERCIAL PRODUCT", "FIXTURE-S4",
         "Operating frequency: 450 kHz", "Maximum range: 60 m",
         "Example use: bathymetric mapping."],
    ],
}


def make_pdf(pages: list[list[str]], path: Path) -> None:
    writer = PdfWriter()
    for lines in pages:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        })
        stream = DecodedStreamObject()
        operators = ["BT /F1 13 Tf 54 730 Td 21 TL"]
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            operators.append(f"({escaped}) Tj T*")
        stream.set_data(("\n".join(operators) + "\nET").encode("ascii"))
        page.replace_contents(stream)
    with path.open("wb") as destination:
        writer.write(destination)


if __name__ == "__main__":
    for filename, pages in FIXTURES.items():
        make_pdf(pages, Path(__file__).resolve().parent / filename)
