#!/usr/bin/env python3
"""Generate realistic dental STL sample files for ISO 18618 IDS demos."""

import io
import math
import os
import struct
import zipfile

FILES_DIR = os.path.join(os.path.dirname(__file__), "files")
os.makedirs(FILES_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# STL binary writer helpers
# ---------------------------------------------------------------------------

def _pack_triangle(n, v1, v2, v3):
    """Pack one triangle into 50 bytes of binary STL."""
    return struct.pack(
        "<12fH",
        n[0], n[1], n[2],
        v1[0], v1[1], v1[2],
        v2[0], v2[1], v2[2],
        v3[0], v3[1], v3[2],
        0,
    )


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _normalize(v):
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if length < 1e-10:
        return (0, 0, 1)
    return (v[0] / length, v[1] / length, v[2] / length)


def _face_normal(v1, v2, v3):
    return _normalize(_cross(_sub(v2, v1), _sub(v3, v1)))


def _write_stl(path, triangles):
    """Write a list of (v1, v2, v3) triangles to a binary STL file."""
    with open(path, "wb") as f:
        header = b"ISO 18618 dental sample STL" + b"\x00" * 53
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for v1, v2, v3 in triangles:
            n = _face_normal(v1, v2, v3)
            f.write(_pack_triangle(n, v1, v2, v3))


# ---------------------------------------------------------------------------
# Primitive shape generators
# ---------------------------------------------------------------------------

def _sphere(cx, cy, cz, r, n_lat=12, n_lon=16):
    """Generate triangles for a UV sphere."""
    tris = []
    for i in range(n_lat):
        theta1 = math.pi * i / n_lat
        theta2 = math.pi * (i + 1) / n_lat
        for j in range(n_lon):
            phi1 = 2 * math.pi * j / n_lon
            phi2 = 2 * math.pi * (j + 1) / n_lon
            p1 = (cx + r * math.sin(theta1) * math.cos(phi1), cy + r * math.sin(theta1) * math.sin(phi1), cz + r * math.cos(theta1))
            p2 = (cx + r * math.sin(theta2) * math.cos(phi1), cy + r * math.sin(theta2) * math.sin(phi1), cz + r * math.cos(theta2))
            p3 = (cx + r * math.sin(theta2) * math.cos(phi2), cy + r * math.sin(theta2) * math.sin(phi2), cz + r * math.cos(theta2))
            p4 = (cx + r * math.sin(theta1) * math.cos(phi2), cy + r * math.sin(theta1) * math.sin(phi2), cz + r * math.cos(theta1))
            tris.append((p1, p2, p3))
            tris.append((p1, p3, p4))
    return tris


def _cylinder(cx, cy, cz, r, h, n_seg=20):
    """Generate triangles for a cylinder along Z axis."""
    tris = []
    for i in range(n_seg):
        a1 = 2 * math.pi * i / n_seg
        a2 = 2 * math.pi * (i + 1) / n_seg
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        # Side faces
        tris.append(((x1, y1, cz), (x2, y2, cz), (x2, y2, cz + h)))
        tris.append(((x1, y1, cz), (x2, y2, cz + h), (x1, y1, cz + h)))
        # Top cap
        tris.append(((cx, cy, cz + h), (x1, y1, cz + h), (x2, y2, cz + h)))
        # Bottom cap
        tris.append(((cx, cy, cz), (x2, y2, cz), (x1, y1, cz)))
    return tris


def _cone(cx, cy, cz, r_bottom, r_top, h, n_seg=20):
    """Generate triangles for a truncated cone (frustum)."""
    tris = []
    for i in range(n_seg):
        a1 = 2 * math.pi * i / n_seg
        a2 = 2 * math.pi * (i + 1) / n_seg
        bx1, by1 = cx + r_bottom * math.cos(a1), cy + r_bottom * math.sin(a1)
        bx2, by2 = cx + r_bottom * math.cos(a2), cy + r_bottom * math.sin(a2)
        tx1, ty1 = cx + r_top * math.cos(a1), cy + r_top * math.sin(a1)
        tx2, ty2 = cx + r_top * math.cos(a2), cy + r_top * math.sin(a2)
        tris.append(((bx1, by1, cz), (bx2, by2, cz), (tx2, ty2, cz + h)))
        tris.append(((bx1, by1, cz), (tx2, ty2, cz + h), (tx1, ty1, cz + h)))
        # Caps
        tris.append(((cx, cy, cz + h), (tx1, ty1, cz + h), (tx2, ty2, cz + h)))
        tris.append(((cx, cy, cz), (bx2, by2, cz), (bx1, by1, cz)))
    return tris


def _box(cx, cy, cz, sx, sy, sz):
    """Generate triangles for a box centered at (cx,cy,cz)."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    corners = [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]
    c = corners
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5),  # bottom, top
        (0, 4, 5, 1), (2, 6, 7, 3),  # front, back
        (0, 3, 7, 4), (1, 5, 6, 2),  # left, right
    ]
    tris = []
    for a, b, cc, d in faces:
        tris.append((c[a], c[b], c[cc]))
        tris.append((c[a], c[cc], c[d]))
    return tris


# ---------------------------------------------------------------------------
# Dental arch generator
# ---------------------------------------------------------------------------

def _dental_arch(n_teeth=14, arch_radius=25.0, z_base=0.0, with_teeth=True, mirror_y=False):
    """Generate a U-shaped dental arch with tooth-like bumps.

    Returns a list of triangles representing an arch base + teeth.
    """
    tris = []
    n_seg = 60
    arch_width = 6.0
    arch_height = 3.0
    y_sign = -1.0 if mirror_y else 1.0

    # Arch base - U-shaped extrusion
    for i in range(n_seg):
        t1 = math.pi * i / n_seg
        t2 = math.pi * (i + 1) / n_seg
        # Outer edge
        ox1 = arch_radius * math.cos(t1)
        oy1 = y_sign * arch_radius * math.sin(t1)
        ox2 = arch_radius * math.cos(t2)
        oy2 = y_sign * arch_radius * math.sin(t2)
        # Inner edge
        ir = arch_radius - arch_width
        ix1 = ir * math.cos(t1)
        iy1 = y_sign * ir * math.sin(t1)
        ix2 = ir * math.cos(t2)
        iy2 = y_sign * ir * math.sin(t2)
        z0 = z_base
        z1 = z_base + arch_height

        # Top surface
        tris.append(((ox1, oy1, z1), (ox2, oy2, z1), (ix2, iy2, z1)))
        tris.append(((ox1, oy1, z1), (ix2, iy2, z1), (ix1, iy1, z1)))
        # Bottom surface
        tris.append(((ox1, oy1, z0), (ix1, iy1, z0), (ix2, iy2, z0)))
        tris.append(((ox1, oy1, z0), (ix2, iy2, z0), (ox2, oy2, z0)))
        # Outer wall
        tris.append(((ox1, oy1, z0), (ox2, oy2, z0), (ox2, oy2, z1)))
        tris.append(((ox1, oy1, z0), (ox2, oy2, z1), (ox1, oy1, z1)))
        # Inner wall
        tris.append(((ix1, iy1, z0), (ix1, iy1, z1), (ix2, iy2, z1)))
        tris.append(((ix1, iy1, z0), (ix2, iy2, z1), (ix2, iy2, z0)))

    if not with_teeth:
        return tris

    # Teeth on the arch
    mid_r = arch_radius - arch_width / 2
    for i in range(n_teeth):
        t = math.pi * (i + 0.5) / n_teeth
        tx = mid_r * math.cos(t)
        ty = y_sign * mid_r * math.sin(t)
        tz = z_base + arch_height

        # Vary tooth size: molars are wider, incisors are narrower
        if i < 2 or i >= n_teeth - 2:
            # Incisors
            tris.extend(_box(tx, ty, tz + 2.5, 2.8, 3.5, 5.0))
        elif i < 4 or i >= n_teeth - 4:
            # Canines/premolars
            tris.extend(_cone(tx, ty, tz, 2.0, 1.2, 5.5, 12))
        else:
            # Molars - wider with rounded top
            tris.extend(_cylinder(tx, ty, tz, 2.5, 3.5, 12))
            tris.extend(_sphere(tx, ty, tz + 3.5, 2.5, 8, 10))

    return tris


def _single_tooth(tooth_type="crown"):
    """Generate a single tooth/restoration shape centered at origin."""
    tris = []
    if tooth_type == "crown":
        # Root (hidden below gumline)
        tris.extend(_cone(0, 0, -6, 1.5, 2.5, 6, 16))
        # Crown body
        tris.extend(_cone(0, 0, 0, 2.5, 3.0, 4, 16))
        # Occlusal surface
        tris.extend(_sphere(0, 0, 4, 3.0, 10, 14))
    elif tooth_type == "implant":
        # Implant screw body
        tris.extend(_cylinder(0, 0, -12, 2.0, 12, 20))
        # Abutment
        tris.extend(_cone(0, 0, 0, 2.0, 2.5, 4, 16))
        # Crown on top
        tris.extend(_sphere(0, 0, 4, 3.0, 10, 14))
    elif tooth_type == "veneer":
        # Thin shell - front face of tooth
        tris.extend(_box(0, 0, 0, 5.0, 0.8, 8.0))
        # Slight curvature on front
        tris.extend(_sphere(0, 0.5, 0, 4.0, 8, 12))
    return tris


# ---------------------------------------------------------------------------
# Dental model generators for each file type
# ---------------------------------------------------------------------------

def make_upper_jaw(path):
    tris = _dental_arch(n_teeth=14, arch_radius=26, z_base=0, with_teeth=True)
    _write_stl(path, tris)


def make_lower_jaw(path):
    tris = _dental_arch(n_teeth=14, arch_radius=24, z_base=0, with_teeth=True, mirror_y=True)
    _write_stl(path, tris)


def make_bite_registration(path):
    """Flat horseshoe-shaped bite plate."""
    tris = _dental_arch(n_teeth=0, arch_radius=25, z_base=0, with_teeth=False)
    _write_stl(path, tris)


def make_prep_scan(path):
    """Arch with a prepared tooth (shorter tooth at position 6)."""
    tris = _dental_arch(n_teeth=12, arch_radius=25, z_base=0, with_teeth=True)
    # Add a prepared tooth stump
    t = math.pi * 5.5 / 12
    mid_r = 25 - 3
    px = mid_r * math.cos(t)
    py = mid_r * math.sin(t)
    tris.extend(_cone(px, py, 3, 2.8, 2.2, 2.5, 16))
    _write_stl(path, tris)


def make_implant_scan(path):
    """Arch with an implant scan body sticking up."""
    tris = _dental_arch(n_teeth=12, arch_radius=24, z_base=0, with_teeth=True, mirror_y=True)
    # Scan body at missing tooth position
    t = math.pi * 8.5 / 12
    mid_r = 24 - 3
    px = mid_r * math.cos(t)
    py = -mid_r * math.sin(t)
    tris.extend(_cylinder(px, py, 3, 1.8, 8, 16))
    tris.extend(_sphere(px, py, 11, 1.8, 8, 10))
    _write_stl(path, tris)


def make_quadrant(path):
    """Half-arch (quadrant) scan."""
    tris = []
    n_teeth = 7
    for i in range(n_teeth):
        x = i * 6.0
        tris.extend(_cylinder(x, 0, 0, 2.5, 3.5, 14))
        tris.extend(_sphere(x, 0, 3.5, 2.5, 8, 10))
    # Gum base
    tris.extend(_box(n_teeth * 3 - 3, 0, -1.5, n_teeth * 6 + 2, 8, 3))
    _write_stl(path, tris)


def make_edentulous_ridge(path, upper=True):
    """Edentulous (toothless) arch for complete denture."""
    tris = _dental_arch(n_teeth=0, arch_radius=25 if upper else 23,
                        z_base=0, with_teeth=False, mirror_y=not upper)
    # Add palate for upper or flat ridge for lower
    if upper:
        tris.extend(_sphere(0, 12, -2, 18, 10, 16))
    _write_stl(path, tris)


def make_smile_design(path):
    """Row of 6 anterior veneers for smile mockup."""
    tris = []
    for i in range(6):
        x = (i - 2.5) * 5.5
        w = 4.5 if abs(i - 2.5) < 1.5 else 3.8
        h = 9.0 if abs(i - 2.5) < 1.5 else 7.5
        tris.extend(_box(x, 0, h / 2, w, 1.5, h))
        tris.extend(_sphere(x, -0.5, h, w / 2, 6, 8))
    _write_stl(path, tris)


def make_denture(path, upper=True):
    """Complete denture with base + artificial teeth."""
    tris = _dental_arch(n_teeth=14, arch_radius=25 if upper else 23,
                        z_base=0, with_teeth=True, mirror_y=not upper)
    if upper:
        # Palate plate
        n_seg = 30
        for i in range(n_seg):
            a1 = math.pi * i / n_seg
            a2 = math.pi * (i + 1) / n_seg
            r = 18
            tris.append(((0, 12, -1), (r * math.cos(a1), 12 + r * math.sin(a1) * 0.5, -1),
                         (r * math.cos(a2), 12 + r * math.sin(a2) * 0.5, -1)))
    _write_stl(path, tris)


def make_jaw_relation(path):
    """Jaw relation record - two arch shapes with a gap."""
    tris = _dental_arch(n_teeth=0, arch_radius=26, z_base=5, with_teeth=False)
    tris.extend(_dental_arch(n_teeth=0, arch_radius=24, z_base=0, with_teeth=False, mirror_y=True))
    _write_stl(path, tris)


def make_pdf(path, size_kb=30):
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
        f.write(b"\x00" * max(0, size_kb * 1024 - len(content)))


def make_jpg(path, size_kb=20):
    with open(path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0")
        f.write(b"\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
        f.write(os.urandom(size_kb * 1024))
        f.write(b"\xff\xd9")


def make_zip(path, size_kb=40):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("sample_data.bin", os.urandom(size_kb * 1024))
    with open(path, "wb") as f:
        f.write(buf.getvalue())


# ---------------------------------------------------------------------------
# File manifest: (filename, generator_function)
# ---------------------------------------------------------------------------

FILES = [
    # 01 - Single Crown
    ("upper_jaw_scan.stl", make_upper_jaw),
    ("lower_jaw_scan.stl", make_lower_jaw),
    ("bite_registration.stl", make_bite_registration),
    # 02 - Bridge
    ("mandible_prep_scan.stl", make_prep_scan),
    ("maxilla_opposing.stl", make_upper_jaw),
    # 03 - Implant
    ("implant_site_scan.stl", make_implant_scan),
    ("cbct_dicom.zip", lambda p: make_zip(p, 80)),
    # 04 - Veneer
    ("upper_prep_scan.stl", make_prep_scan),
    ("lower_opposing.stl", make_lower_jaw),
    ("smile_photo_front.jpg", lambda p: make_jpg(p, 30)),
    ("smile_design_mockup.stl", make_smile_design),
    # 05 - Inlay/Onlay
    ("quadrant_2_prep.stl", make_quadrant),
    ("quadrant_2_opposing.stl", make_quadrant),
    # 06 - RPD
    ("upper_arch_edentulous.stl", lambda p: make_edentulous_ridge(p, upper=True)),
    ("lower_arch_full.stl", make_lower_jaw),
    # bite_registration.stl already created above
    # 07 - Ortho
    ("upper_arch_stage5.stl", make_upper_jaw),
    ("lower_arch_stage5.stl", make_lower_jaw),
    ("treatment_plan.pdf", lambda p: make_pdf(p, 40)),
    # 08 - Full Denture
    ("upper_edentulous_ridge.stl", lambda p: make_edentulous_ridge(p, upper=True)),
    ("lower_edentulous_ridge.stl", lambda p: make_edentulous_ridge(p, upper=False)),
    ("jaw_relation_record.stl", make_jaw_relation),
    ("facebow_record.pdf", lambda p: make_pdf(p, 20)),
    # 09 - Multi-case Broker
    ("yang_upper_scan.stl", make_upper_jaw),
    ("yang_lower_scan.stl", make_lower_jaw),
    ("moon_upper_scan.stl", make_upper_jaw),
    ("moon_lower_scan.stl", make_lower_jaw),
    ("ryu_implant_scan.stl", make_implant_scan),
]


if __name__ == "__main__":
    total = 0
    for filename, generator in FILES:
        path = os.path.join(FILES_DIR, filename)
        # Always regenerate to update geometry
        generator(path)
        size = os.path.getsize(path)
        total += 1
        print(f"  Created: {filename} ({size / 1024:.1f} KB)")
    print(f"\nDone. {total} files created in {FILES_DIR}")
