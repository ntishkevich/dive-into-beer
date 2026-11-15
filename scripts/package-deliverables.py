from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import zipfile

argparse.ArgumentParser(description='Package the public beer site.').parse_args()

root = Path(__file__).resolve().parents[1]
out = root / 'output'
devices = ('mobile', 'desktop')
categories = ('performance', 'accessibility', 'best-practices', 'seo')
index_bytes = (root / 'index.html').read_bytes()
digest = hashlib.sha256(index_bytes).hexdigest()

for device in devices:
    path = out / 'site-audits' / f'production-{device}.summary.json'
    try:
        summary = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        summary = None
    if not isinstance(summary, dict) or summary.get('artifactSha256') != digest:
        raise SystemExit(f'No current {device} Lighthouse summary. Run node scripts/audit-atlas.mjs.')

    scores = summary.get('scores')
    if not isinstance(scores, dict) or any(
        type(scores.get(category)) not in (int, float) or not 90 <= scores[category] <= 100
        for category in categories
    ):
        raise SystemExit(f'{device} Lighthouse must score 90–100 in all four categories.')

with tempfile.TemporaryDirectory(prefix='beer-package-', dir=out) as temp:
    staged = Path(temp) / 'beer-site.zip'
    with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('index.html', index_bytes)
        archive.write(root / 'assets/site-readme.md', 'README.md')
        archive.writestr('.nojekyll', '')
    staged.replace(out / staged.name)

print('Prepared beer-site.zip')
