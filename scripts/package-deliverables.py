from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import zipfile

parser = argparse.ArgumentParser(description='Package the public beer site and source materials.')
parser.add_argument('--course-only', action='store_true', help='Update only the source archive, keeping the public site archive unchanged.')
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
out = root / 'output'
out.mkdir(exist_ok=True)
devices = ('mobile', 'desktop')
categories = ('performance', 'accessibility', 'best-practices', 'seo')
atlas = out / 'beer-atlas.html'
atlas_bytes = atlas.read_bytes() if atlas.is_file() else None
digest = hashlib.sha256(atlas_bytes).hexdigest() if atlas_bytes is not None else None


def matching_audit(path):
    if digest is None:
        return None
    try:
        report = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if isinstance(report, dict) and report.get('artifactSha256') == digest:
        return report
    return None


audit_dir = out / 'site-audits'
summaries = {
    device: matching_audit(audit_dir / f'production-{device}.summary.json')
    for device in devices
}

if not args.course_only:
    index_bytes = (root / 'index.html').read_bytes()
    if atlas_bytes != index_bytes:
        raise SystemExit('index.html and output/beer-atlas.html differ. Run node scripts/build-atlas.cjs.')
    for device, summary in summaries.items():
        if summary is None:
            raise SystemExit(f'No current {device} Lighthouse summary. Run node scripts/audit-atlas.mjs.')
        scores = summary.get('scores')
        if not isinstance(scores, dict) or any(
            type(scores.get(category)) not in (int, float) or not 90 <= scores[category] <= 100
            for category in categories
        ):
            raise SystemExit(f'{device} Lighthouse must score 90–100 in all four categories.')

files = [root / name for name in ['index.html', '.nojekyll', 'README.md', 'MISSION.md', 'RESOURCES.md', 'AGENTS.md']]
for folder in ['assets', 'lessons', 'reference', 'scripts']:
    files.extend((root / folder).glob('*'))
files.extend([atlas, out / 'beer-atlas.pdf'])
if matching_audit(out / 'beer-design-audit.json'):
    files.extend([out / 'beer-design-audit.html', out / 'beer-design-audit.json'])
for device, summary in summaries.items():
    if summary is not None:
        files.extend(audit_dir.glob(f'production-{device}.*'))
    elif (audit_dir / f'production-{device}.summary.json').is_file():
        print(f'Omitted stale {device} Lighthouse reports from the source archive.')

with tempfile.TemporaryDirectory(prefix='beer-package-', dir=out) as temp:
    staged = Path(temp)
    if not args.course_only:
        with zipfile.ZipFile(staged / 'beer-site.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('index.html', index_bytes)
            archive.write(root / 'assets/site-readme.md', 'README.md')
            archive.writestr('.nojekyll', '')
    with zipfile.ZipFile(staged / 'beer-course.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            if file.is_file():
                archive.write(file, file.relative_to(root).as_posix())
    for archive in staged.iterdir():
        archive.replace(out / archive.name)

print('Prepared beer-course.zip' if args.course_only else 'Prepared beer-site.zip and beer-course.zip')
