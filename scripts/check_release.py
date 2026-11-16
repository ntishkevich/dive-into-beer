import argparse
import json
from hashlib import sha256
from pathlib import Path, PurePosixPath
from shutil import copyfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from package_deliverables import package_site
from site_files import ROOT, read_site_snapshot, site_file_hashes


def assert_rejected(fixture, message):
    try:
        package_site(fixture)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"ZIP packaging accepted an invalid {message}")


def main(argv=None):
    argparse.ArgumentParser(description="Check packaging and stale audit rejection.").parse_args(
        argv
    )
    root = ROOT
    temporary_root = root / "tmp"
    temporary_root.mkdir(exist_ok=True)
    temporary_root = temporary_root.resolve()
    with TemporaryDirectory(prefix="release-check-", dir=temporary_root) as directory:
        fixture = Path(directory).resolve()
        assert fixture.parent == temporary_root
        for folder in ("assets", "icons", "output/site-audits"):
            (fixture / folder).mkdir(parents=True)

        manifest = json.loads((root / "manifest.webmanifest").read_text(encoding="utf-8"))
        original_icon = PurePosixPath(manifest["icons"][0]["src"]).as_posix()
        renamed_icon = "icons/renamed-192.png"
        manifest["icons"][0]["src"] = "./" + renamed_icon
        files = {
            "index.html",
            "favicon.ico",
            "icon.svg",
            "apple-touch-icon.png",
            "assets/social-cover.jpg",
            *(PurePosixPath(icon["src"]).as_posix() for icon in manifest["icons"]),
        }
        for name in (files - {renamed_icon}) | {"assets/site-readme.md"}:
            (fixture / name).parent.mkdir(parents=True, exist_ok=True)
            copyfile(root / name, fixture / name)
        # Leave the old asset in the directory to catch an obsolete hard-coded list.
        (fixture / original_icon).parent.mkdir(parents=True, exist_ok=True)
        copyfile(root / original_icon, fixture / original_icon)
        copyfile(root / original_icon, fixture / renamed_icon)
        (fixture / "manifest.webmanifest").write_text(json.dumps(manifest), encoding="utf-8")
        files.add("manifest.webmanifest")
        hashes = {name: sha256((fixture / name).read_bytes()).hexdigest() for name in files}
        assert site_file_hashes(read_site_snapshot(fixture)) == hashes
        report = {
            "artifactSha256": hashes["index.html"],
            "siteFileHashes": hashes,
            "scores": dict.fromkeys(("performance", "accessibility", "best-practices", "seo"), 100),
        }
        for device in ("mobile", "desktop"):
            summary = fixture / "output/site-audits" / f"production-{device}.summary.json"
            summary.write_text(json.dumps({**report, "device": device}), encoding="utf-8")

        archive = package_site(fixture)
        with ZipFile(archive) as site:
            assert set(site.namelist()) == files | {"README.md", ".nojekyll"}
            assert site.read(renamed_icon) == (fixture / renamed_icon).read_bytes()
            assert site.testzip() is None

        previous = archive.read_bytes()
        for name, replacement in [
            ("manifest.webmanifest", b"invalid JSON"),
            (renamed_icon, b"invalid image"),
        ]:
            file = fixture / name
            original = file.read_bytes()
            file.write_bytes(replacement)
            assert_rejected(fixture, name)
            assert archive.read_bytes() == previous
            file.write_bytes(original)

        desktop_summary = fixture / "output/site-audits/production-desktop.summary.json"
        desktop_summary.write_text(json.dumps({**report, "device": "mobile"}), encoding="utf-8")
        assert_rejected(fixture, "desktop")
        assert archive.read_bytes() == previous

    print(
        "Release checks passed: manifest icon included, stale resources rejected, previous ZIP preserved."
    )


if __name__ == "__main__":
    main()
