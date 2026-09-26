# -*- coding: utf-8 -*-
"""Generate the Windows version resource from version.APP_VERSION."""
from pathlib import Path

from version import APP_VERSION


def _version_tuple(value):
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"APP_VERSION must use X.Y.Z format: {value!r}")
    return tuple(int(part) for part in parts) + (0,)


def main():
    version_tuple = _version_tuple(APP_VERSION)
    dotted_version = ".".join(str(part) for part in version_tuple)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', ''),
        StringStruct('FileDescription', '인천과학고 급식 및 시간표 바탕화면 프로그램'),
        StringStruct('FileVersion', '{dotted_version}'),
        StringStruct('InternalName', 'hataewook_program'),
        StringStruct('LegalCopyright', ''),
        StringStruct('OriginalFilename', '하태욱 프로그램.exe'),
        StringStruct('ProductName', '하태욱 프로그램'),
        StringStruct('ProductVersion', '{dotted_version}')])
      ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    output = Path(__file__).with_name("windows_version_info.txt")
    output.write_text(content, encoding="utf-8")
    print(f"Generated {output.name} for {APP_VERSION}")


if __name__ == "__main__":
    main()
