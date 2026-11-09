"""Compile Django .po files to .mo using only Python's standard library.

Usage: python scripts/compile_catalogs.py. Django reads the generated .mo files
at runtime; this helper avoids requiring GNU gettext on Windows/AWS Academy.
"""
import ast
import struct
from pathlib import Path


def read_po(path):
    catalog, key, value, active = {}, None, [], None
    for raw in path.read_text(encoding="utf-8").splitlines() + [""]:
        line = raw.strip()
        if line.startswith("msgid "):
            if key is not None:
                catalog[key] = "".join(value)
            key, value, active = ast.literal_eval(line[6:]), [], "id"
        elif line.startswith("msgstr "):
            value, active = [ast.literal_eval(line[7:])], "str"
        elif line.startswith('"') and active:
            value.append(ast.literal_eval(line))
        elif not line and key is not None:
            catalog[key] = "".join(value) if active == "str" else ""
            key, value, active = None, [], None
    # msgid "" contiene los metadatos del catálogo (en particular charset).
    # Aunque no sea una cadena traducible, GNUTranslations lo necesita para
    # decodificar correctamente los msgid/msgstr UTF-8 del archivo .mo.
    return {key: val for key, val in catalog.items() if val}


def write_mo(catalog, target):
    ids = sorted(catalog)
    originals = [key.encode("utf-8") for key in ids]
    translations = [catalog[key].encode("utf-8") for key in ids]
    count, header_size = len(ids), 7 * 4
    original_table = header_size
    translation_table = original_table + count * 8
    strings_offset = translation_table + count * 8
    original_blob, translation_blob = b"", b""
    original_entries, translation_entries = [], []
    for item in originals:
        original_entries.append((len(item), strings_offset + len(original_blob)))
        original_blob += item + b"\0"
    for item in translations:
        translation_entries.append((len(item), strings_offset + len(original_blob) + len(translation_blob)))
        translation_blob += item + b"\0"
    data = struct.pack("<7I", 0x950412DE, 0, count, original_table, translation_table, 0, 0)
    data += b"".join(struct.pack("<2I", *entry) for entry in original_entries)
    data += b"".join(struct.pack("<2I", *entry) for entry in translation_entries)
    target.write_bytes(data + original_blob + translation_blob)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for source in (root / "locale").glob("*/LC_MESSAGES/django.po"):
        destination = source.with_suffix(".mo")
        write_mo(read_po(source), destination)
        print(f"Compiled {source.relative_to(root)} -> {destination.relative_to(root)}")
