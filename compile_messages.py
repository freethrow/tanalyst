#!/usr/bin/env python
"""
Simple script to compile .po files to .mo files without requiring gettext tools.
This is a basic implementation for development purposes.
"""

import os
import struct
import array


def compile_po_to_mo(po_file, mo_file):
    """
    Compile a .po file to .mo file format.
    This is a simplified version that handles basic translations.
    """

    # Read the .po file
    with open(po_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse translations
    translations = {}
    lines = content.split("\n")
    msgid = None
    msgstr = None

    for line in lines:
        line = line.strip()
        if line.startswith('msgid "') and line.endswith('"'):
            msgid = line[7:-1]  # Remove 'msgid "' and '"'
        elif line.startswith('msgstr "') and line.endswith('"'):
            msgstr = line[8:-1]  # Remove 'msgstr "' and '"'
            if msgid is not None and msgstr:
                translations[msgid] = msgstr
            msgid = None
            msgstr = None

    # Create .mo file content
    keys = sorted(translations.keys())
    values = [translations[k] for k in keys]

    # MO file format (simplified)
    koffsets = []
    voffsets = []
    kencoded = []
    vencoded = []

    for k, v in zip(keys, values):
        kencoded.append(k.encode("utf-8"))
        vencoded.append(v.encode("utf-8"))

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart
    for k in kencoded:
        valuestart += len(k)

    koffsets = []
    voffsets = []

    offset = keystart
    for k in kencoded:
        koffsets.append((len(k), offset))
        offset += len(k)

    offset = valuestart
    for v in vencoded:
        voffsets.append((len(v), offset))
        offset += len(v)

    # Write .mo file
    with open(mo_file, "wb") as f:
        # Magic number
        f.write(struct.pack("<I", 0x950412DE))
        # Version
        f.write(struct.pack("<I", 0))
        # Number of entries
        f.write(struct.pack("<I", len(keys)))
        # Offset of key table
        f.write(struct.pack("<I", 7 * 4))
        # Offset of value table
        f.write(struct.pack("<I", 7 * 4 + 8 * len(keys)))
        # Hash table size
        f.write(struct.pack("<I", 0))
        # Offset of hash table
        f.write(struct.pack("<I", 0))

        # Key offsets
        for length, offset in koffsets:
            f.write(struct.pack("<I", length))
            f.write(struct.pack("<I", offset))

        # Value offsets
        for length, offset in voffsets:
            f.write(struct.pack("<I", length))
            f.write(struct.pack("<I", offset))

        # Keys
        for k in kencoded:
            f.write(k)

        # Values
        for v in vencoded:
            f.write(v)


def main():
    """Compile all .po files in the locale directory."""

    locale_dir = "locale"

    if not os.path.exists(locale_dir):
        print(f"Locale directory '{locale_dir}' not found.")
        return

    compiled_count = 0

    for lang_dir in os.listdir(locale_dir):
        lang_path = os.path.join(locale_dir, lang_dir)
        if os.path.isdir(lang_path):
            lc_messages_path = os.path.join(lang_path, "LC_MESSAGES")
            if os.path.exists(lc_messages_path):
                po_file = os.path.join(lc_messages_path, "django.po")
                mo_file = os.path.join(lc_messages_path, "django.mo")

                if os.path.exists(po_file):
                    try:
                        compile_po_to_mo(po_file, mo_file)
                        print(f"✅ Compiled {po_file} -> {mo_file}")
                        compiled_count += 1
                    except Exception as e:
                        print(f"❌ Error compiling {po_file}: {e}")

    print(f"\n🎉 Compiled {compiled_count} translation files.")
    print("Your Django i18n setup is ready!")


if __name__ == "__main__":
    main()
