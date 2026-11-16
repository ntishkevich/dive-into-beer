"""Read the canonical Markdown source catalogue."""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "assets/beer-sources.md"
RECORD = re.compile(
    r"## ([0-9]{2,}) · ([a-z][a-z0-9-]*)\n\n- Название: (.+)\n"
    r"- Ссылка: <([^\s<>]+)>\n- Группа: (.+)\n\n([\s\S]+)"
)


def read_sources(file=SOURCE_FILE):
    heading, *sections = re.split(r"\n(?=## )", file.read_text(encoding="utf-8").strip())
    if heading.strip() != "# Источники атласа" or not sections:
        raise ValueError(f"Expected a source catalogue in {file}")

    ids = set()
    numbers = set()
    sources = []
    for section in sections:
        match = RECORD.fullmatch(section.strip())
        if not match:
            raise ValueError(f"Invalid source record in {file}: {section.splitlines()[0]}")
        number, source_id, title, url, group, note = match.groups()
        n = int(number)
        if not title.strip() or not group.strip():
            raise ValueError(f"Missing source title or group in {file}: {source_id}")
        if not 1 <= n <= 2**53 - 1 or source_id in ids or n in numbers:
            raise ValueError(f"Invalid or duplicate source ID/number in {file}: {source_id} ({n})")
        try:
            address = urlsplit(url)
            if not re.match(r"https?://", url, re.IGNORECASE) or not address.hostname:
                raise ValueError
            address.port  # Validate the optional port too.
        except ValueError:
            raise ValueError(
                f"Expected an absolute HTTP(S) URL for source {source_id} in {file}"
            ) from None
        ids.add(source_id)
        numbers.add(n)
        sources.append(
            dict(id=source_id, n=n, title=title.strip(), note=note, url=url, group=group.strip())
        )
    return sorted(sources, key=lambda source: source["n"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export the verified source catalogue as JSON.")
    parser.add_argument(
        "--output", type=Path, help="JSON destination. Defaults to standard output."
    )
    args = parser.parse_args(argv)
    try:
        payload = json.dumps(read_sources(), ensure_ascii=False, separators=(",", ":")).encode()
        if args.output is None:
            sys.stdout.buffer.write(payload)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(payload)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
