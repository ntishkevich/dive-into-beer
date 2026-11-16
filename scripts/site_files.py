"""The files served by preview and checked by the release audit."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "manifest.webmanifest"
DEVICES = ("mobile", "desktop")
CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
FIXED_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "favicon.ico": "image/vnd.microsoft.icon",
    "icon.svg": "image/svg+xml",
    "apple-touch-icon.png": "image/png",
    MANIFEST: "application/manifest+json; charset=utf-8",
    "assets/social-cover.jpg": "image/jpeg",
}
RELATIVE_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*")
IMAGE_MIME = re.compile(r"image/[a-z0-9.+-]+", re.IGNORECASE)


@dataclass(frozen=True)
class SiteFile:
    body: bytes
    content_type: str


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_site_file_types(manifest_bytes):
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeError, ValueError) as error:
        raise ValueError(f"Invalid {MANIFEST}: {error}") from error
    icons = manifest.get("icons") if isinstance(manifest, dict) else None
    if not isinstance(icons, list) or not icons:
        raise ValueError(f"No icons are declared in {MANIFEST}")

    types = FIXED_TYPES.copy()
    for icon in icons:
        href = icon.get("src") if isinstance(icon, dict) else None
        name = re.sub(r"^(?:\./)+", "", href) if isinstance(href, str) else ""
        known_type = types.get(name)
        if not RELATIVE_FILE.fullmatch(name) or (
            known_type and not known_type.startswith("image/")
        ):
            raise ValueError(f"Expected a relative icon file in {MANIFEST}: {href}")
        content_type = icon.get("type")
        if "type" in icon and (
            not isinstance(content_type, str) or not IMAGE_MIME.fullmatch(content_type)
        ):
            raise ValueError(f"Invalid icon MIME type in {MANIFEST}: {name}")
        types[name] = known_type or content_type or "application/octet-stream"
    return types


def read_site_snapshot(root=ROOT):
    root = root.resolve()
    manifest_path = (root / MANIFEST).resolve()
    if not manifest_path.is_relative_to(root):
        raise ValueError(f"Site file is outside the repository: {MANIFEST}")
    manifest = manifest_path.read_bytes()
    snapshot = {}
    for name, content_type in read_site_file_types(manifest).items():
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Site file is outside the repository: {name}")
        snapshot[name] = SiteFile(manifest if name == MANIFEST else path.read_bytes(), content_type)
    return snapshot


def site_file_hashes(snapshot):
    return {name: sha256(file.body).hexdigest() for name, file in snapshot.items()}


def read_audited_site(root=ROOT):
    snapshot = read_site_snapshot(root)
    hashes = site_file_hashes(snapshot)
    reports = []
    for device in DEVICES:
        path = root / "output/site-audits" / f"production-{device}.summary.json"
        refresh = "Run python scripts/atlas.py audit."
        try:
            report = read_json(path)
        except (OSError, ValueError):
            raise ValueError(f"No {device} Lighthouse summary. {refresh}") from None
        if not isinstance(report, dict) or report.get("device") != device:
            raise ValueError(f"Invalid {device} Lighthouse summary. {refresh}")
        measured = report.get("siteFileHashes")
        if not isinstance(measured, dict) or report.get("artifactSha256") != measured.get(
            "index.html"
        ):
            raise ValueError(f"Invalid file hashes in {device} Lighthouse summary. {refresh}")
        if measured != hashes:
            changed = sorted(
                name
                for name in measured.keys() | hashes.keys()
                if measured.get(name) != hashes.get(name)
            )
            raise ValueError(f"Audited site files have changed: {', '.join(changed)}. {refresh}")
        scores = report.get("scores")
        if not isinstance(scores, dict) or any(
            type(scores.get(category)) not in (int, float) or not 90 <= scores[category] <= 100
            for category in CATEGORIES
        ):
            raise ValueError(f"{device} Lighthouse must score 90–100 in all four categories.")
        reports.append(report)
    return snapshot, reports
