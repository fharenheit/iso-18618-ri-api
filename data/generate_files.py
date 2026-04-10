#!/usr/bin/env python3
"""Generate dummy attachment files for sample IDS XML data."""

import os
import random

FILES_DIR = os.path.join(os.path.dirname(__file__), "files")
os.makedirs(FILES_DIR, exist_ok=True)


def make_stl(path, size_kb=50):
    """Create a minimal dummy STL binary file."""
    with open(path, "wb") as f:
        # STL binary header (80 bytes) + triangle count (4 bytes)
        f.write(b"Binary STL - ISO 18618 sample" + b"\x00" * 50)
        num_triangles = size_kb * 10
        f.write(num_triangles.to_bytes(4, "little"))
        # Each triangle = 50 bytes (normal + 3 vertices + attribute)
        for _ in range(num_triangles):
            f.write(os.urandom(50))


def make_pdf(path, size_kb=30):
    """Create a minimal dummy PDF file."""
    content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (ISO 18618 Sample) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
300
%%EOF
"""
    with open(path, "wb") as f:
        f.write(content)
        # Pad to desired size
        f.write(b"\x00" * max(0, size_kb * 1024 - len(content)))


def make_jpg(path, size_kb=20):
    """Create a minimal dummy JPEG file."""
    with open(path, "wb") as f:
        # JPEG SOI marker + JFIF header
        f.write(b"\xff\xd8\xff\xe0")
        f.write(b"\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
        f.write(os.urandom(size_kb * 1024))
        f.write(b"\xff\xd9")  # EOI marker


def make_zip(path, size_kb=40):
    """Create a minimal dummy ZIP file."""
    import zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("sample_data.bin", os.urandom(size_kb * 1024))
    with open(path, "wb") as f:
        f.write(buf.getvalue())


# File definitions per sample IDS
FILES = {
    "01": [
        ("upper_jaw_scan.stl", "stl", 50),
        ("lower_jaw_scan.stl", "stl", 48),
        ("bite_registration.stl", "stl", 20),
    ],
    "02": [
        ("mandible_prep_scan.stl", "stl", 55),
        ("maxilla_opposing.stl", "stl", 52),
    ],
    "03": [
        ("implant_site_scan.stl", "stl", 60),
        ("cbct_dicom.zip", "zip", 80),
    ],
    "04": [
        ("upper_prep_scan.stl", "stl", 53),
        ("lower_opposing.stl", "stl", 50),
        ("smile_photo_front.jpg", "jpg", 30),
        ("smile_design_mockup.stl", "stl", 40),
    ],
    "05": [
        ("quadrant_2_prep.stl", "stl", 35),
        ("quadrant_2_opposing.stl", "stl", 33),
    ],
    "06": [
        ("upper_arch_edentulous.stl", "stl", 58),
        ("lower_arch_full.stl", "stl", 52),
        ("bite_registration.stl", "stl", 22),
    ],
    "07": [
        ("upper_arch_stage5.stl", "stl", 55),
        ("lower_arch_stage5.stl", "stl", 53),
        ("treatment_plan.pdf", "pdf", 40),
    ],
    "08": [
        ("upper_edentulous_ridge.stl", "stl", 45),
        ("lower_edentulous_ridge.stl", "stl", 43),
        ("jaw_relation_record.stl", "stl", 25),
        ("facebow_record.pdf", "pdf", 20),
    ],
    "09": [
        ("yang_upper_scan.stl", "stl", 48),
        ("yang_lower_scan.stl", "stl", 47),
        ("moon_upper_scan.stl", "stl", 50),
        ("moon_lower_scan.stl", "stl", 49),
        ("ryu_implant_scan.stl", "stl", 56),
    ],
    "10": [],  # Notification - no files
}

GENERATORS = {
    "stl": make_stl,
    "pdf": make_pdf,
    "jpg": make_jpg,
    "zip": make_zip,
}

if __name__ == "__main__":
    total = 0
    for prefix, file_list in FILES.items():
        for filename, filetype, size_kb in file_list:
            path = os.path.join(FILES_DIR, filename)
            if not os.path.exists(path):
                GENERATORS[filetype](path, size_kb)
                total += 1
                print(f"  Created: {filename} ({size_kb} KB)")
            else:
                print(f"  Exists:  {filename}")
    print(f"\nDone. {total} files created in {FILES_DIR}")
