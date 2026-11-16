"""Package exactly the static files covered by the Lighthouse reports."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from site_files import ROOT, read_audited_site


def package_site(root=ROOT):
    site, _ = read_audited_site(root)
    output = root / "output"
    destination = output / "beer-site.zip"
    # Write beside the destination so a failed check or write cannot replace the existing ZIP.
    with TemporaryDirectory(prefix="beer-package-", dir=output) as temp:
        staged = Path(temp) / destination.name
        with ZipFile(staged, "w", ZIP_DEFLATED) as archive:
            for name, file in site.items():
                archive.writestr(name, file.body)
            archive.write(root / "assets/site-readme.md", "README.md")
            archive.writestr(".nojekyll", "")
        staged.replace(destination)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description="Package the public beer site.")
    parser.parse_args(argv)
    try:
        print(f"Prepared {package_site().name}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
