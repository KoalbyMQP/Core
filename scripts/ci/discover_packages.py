#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
PKGS_DIR = ROOT / "pkgs"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("_", "-")
    return re.sub(r"[^a-z0-9.-]+", "-", value).strip("-")


def package_xml_name(package_xml: Path) -> str:
    root = ElementTree.parse(package_xml).getroot()
    name = root.findtext("name")
    if not name:
        raise ValueError(f"missing <name> in {package_xml}")
    return name.strip()


def image_name(pkg_dir: Path) -> str:
    zaraos = pkg_dir / "zaraos.json"
    if zaraos.exists():
      data = json.loads(zaraos.read_text())
      image = data.get("image", "").strip()
      if image:
          return slugify(image.rsplit("/", 1)[-1])
    return slugify(pkg_dir.name)


def discover() -> list[dict[str, str]]:
    packages: list[dict[str, str]] = []
    for pkg_dir in sorted(PKGS_DIR.iterdir()):
        if not pkg_dir.is_dir():
            continue
        package_xml = pkg_dir / "package.xml"
        if not package_xml.exists():
            continue
        ros_package = package_xml_name(package_xml)
        custom_dockerfile = pkg_dir / "Dockerfile"
        if not custom_dockerfile.exists():
            raise FileNotFoundError(f"missing Dockerfile for package {pkg_dir.name}")
        packages.append(
            {
                "package_dir": pkg_dir.name,
                "package_name": ros_package,
                "image_name": image_name(pkg_dir),
                "dockerfile": str(custom_dockerfile.relative_to(ROOT)),
            }
        )
    return packages


def main() -> int:
    packages = discover()
    if not packages:
        print("[]")
        return 0
    json.dump(packages, sys.stdout, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
