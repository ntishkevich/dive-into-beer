"""Shared Chrome lifecycle and report files for the browser checks."""

import json
import os
from contextlib import contextmanager
from pathlib import Path

from site_files import ROOT

TEMP = ROOT / "tmp"


@contextmanager
def chrome():
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:
        if error.name != "playwright":
            raise
        raise SystemExit(
            "Install the Python check dependencies from scripts/requirements.txt."
        ) from error

    TEMP.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        executable = os.environ.get("CHROME_PATH")
        options = (
            {"executable_path": Path(executable).resolve()} if executable else {"channel": "chrome"}
        )
        browser = playwright.chromium.launch(headless=True, **options)
        try:
            yield browser
        finally:
            browser.close()


def write_report(name, report):
    (TEMP / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report))
