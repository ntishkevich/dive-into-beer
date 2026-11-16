"""Audit the exact static snapshot with the Lighthouse CLI."""

import argparse
import json
import os
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from tempfile import TemporaryDirectory
from urllib.parse import urljoin
from urllib.request import urlopen

from preview_atlas import preview_server, project_path
from site_files import CATEGORIES, DEVICES, ROOT, read_json, read_site_snapshot, site_file_hashes

METRICS = (
    "first-contentful-paint",
    "largest-contentful-paint",
    "total-blocking-time",
    "cumulative-layout-shift",
    "speed-index",
)


def lighthouse_command():
    configured = os.environ.get("LIGHTHOUSE_PATH")
    if configured:
        return [configured]
    entry = ROOT / "tmp/lighthouse-tools/node_modules/lighthouse/cli/index.js"
    node = which(os.environ.get("BEER_NODE") or "node")
    if not node or not entry.is_file():
        raise ValueError(
            "Lighthouse CLI is unavailable. Run npm install --prefix tmp/lighthouse-tools "
            "lighthouse@13.6.0 with Node.js installed, or set LIGHTHOUSE_PATH."
        )
    return [node, str(entry)]


def summarize(result, device, hashes, size):
    if error := result.get("runtimeError"):
        raise ValueError(f"{device} Lighthouse: {error.get('message', error)}")
    failures = [
        dict(
            id=audit["id"],
            title=audit["title"],
            score=audit["score"],
            items=audit["details"]["items"][:4],
        )
        for audit in result["audits"].values()
        if audit.get("score") is not None
        and audit["score"] < 1
        and (audit.get("details") or {}).get("items")
    ]
    return {
        "name": "production",
        "device": device,
        "lighthouse": result["lighthouseVersion"],
        "chrome": result["environment"]["hostUserAgent"],
        "artifactSha256": hashes["index.html"],
        "siteFileHashes": hashes,
        "bytes": size,
        "scores": {
            category: int(result["categories"][category]["score"] * 100 + 0.5)
            for category in CATEGORIES
        },
        "metrics": {
            metric: {
                "value": result["audits"][metric]["numericValue"],
                "display": result["audits"][metric].get("displayValue"),
            }
            for metric in METRICS
        },
        "failures": failures,
        "warnings": result["runWarnings"],
    }


def audit():
    lighthouse = lighthouse_command()
    site = read_site_snapshot()
    hashes = site_file_hashes(site)
    output = ROOT / "output/site-audits"
    output.mkdir(parents=True, exist_ok=True)
    with (
        TemporaryDirectory(prefix="lighthouse-", dir=output) as directory,
        preview_server(snapshot=site) as base,
    ):
        url = base + project_path()
        for name, file in site.items():
            with urlopen(
                url if name == "index.html" else urljoin(url, name), timeout=10
            ) as response:
                if response.read() != file.body:
                    raise ValueError(f"Preview content differs from the site snapshot: {name}")

        staged = Path(directory)
        reports = []
        for device in DEVICES:
            stem = f"production-{device}"
            args = [
                *lighthouse,
                url,
                f"--only-categories={','.join(CATEGORIES)}",
                "--output=html",
                "--output=json",
                f"--output-path={staged / stem}",
                "--chrome-flags=--headless=new",
                "--quiet",
            ]
            if device == "desktop":
                args.append("--preset=desktop")
            run(args, check=True)
            result = read_json(staged / f"{stem}.report.json")
            report = summarize(result, device, hashes, len(site["index.html"].body))
            (staged / f"{stem}.summary.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
            )
            reports.append(report)
        # Publish the pair only after both profiles have run successfully.
        for device in DEVICES:
            for suffix in ("report.html", "report.json", "summary.json"):
                name = f"production-{device}.{suffix}"
                (staged / name).replace(output / name)
        return reports


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run Lighthouse for mobile and desktop.")
    parser.parse_args(argv)
    try:
        for report in audit():
            print(
                json.dumps(
                    {
                        "device": report["device"],
                        "scores": report["scores"],
                        "diagnostics": [entry["id"] for entry in report["failures"]],
                    }
                )
            )
    except (OSError, ValueError, CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
