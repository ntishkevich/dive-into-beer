import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { once } from 'node:events';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { startPreview } from './preview-atlas.cjs';

const dependencies = new URL('../tmp/lighthouse-tools/node_modules/', import.meta.url);
const { default: lighthouse } = await import(new URL('lighthouse/core/index.js', dependencies));
const { default: desktopConfig } = await import(new URL('lighthouse/core/config/desktop-config.js', dependencies));
const { launch } = await import(new URL('chrome-launcher/dist/index.js', dependencies));

const document = await readFile(new URL('../output/beer-atlas.html', import.meta.url));
const sha256 = createHash('sha256').update(document).digest('hex');
const categories = ['performance', 'accessibility', 'best-practices', 'seo'];
const metrics = [
  'first-contentful-paint', 'largest-contentful-paint', 'total-blocking-time',
  'cumulative-layout-shift', 'speed-index',
];
const auditDir = new URL('../output/site-audits/', import.meta.url);
const server = startPreview(0);

try {
  await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}/beer/`;

  async function verifyServedPage() {
    const response = await fetch(url);
    assert(response.ok && document.equals(Buffer.from(await response.arrayBuffer())),
      'Preview content differs from output/beer-atlas.html. Run node scripts/build-atlas.cjs.');
  }

  await mkdir(auditDir, { recursive: true });
  for (const [device, config] of [['mobile', undefined], ['desktop', desktopConfig]]) {
    await verifyServedPage();
    const chrome = await launch({ chromeFlags: ['--headless=new'] });
    try {
      const { lhr, report } = await lighthouse(url, {
        port: chrome.port,
        onlyCategories: categories,
        logLevel: 'error',
        output: ['html', 'json'],
      }, config);
      assert(!lhr.runtimeError, JSON.stringify(lhr.runtimeError));
      await verifyServedPage();
      const scores = Object.fromEntries(categories.map(id => [
        id, Math.round(lhr.categories[id].score * 100),
      ]));
      const summary = {
        name: 'production',
        device,
        lighthouse: lhr.lighthouseVersion,
        chrome: lhr.environment.hostUserAgent,
        artifactSha256: sha256,
        bytes: document.length,
        scores,
        metrics: Object.fromEntries(metrics.map(id => [
          id, { value: lhr.audits[id].numericValue, display: lhr.audits[id].displayValue },
        ])),
        failures: Object.values(lhr.audits)
          .filter(audit => audit.score !== null && audit.score < 1 && audit.details?.items?.length)
          .map(({ id, title, score, details }) => ({ id, title, score, items: details.items.slice(0, 4) })),
        warnings: lhr.runWarnings,
      };
      const base = `production-${device}`;
      await writeFile(new URL(base + '.report.html', auditDir), report[0]);
      await writeFile(new URL(base + '.report.json', auditDir), report[1]);
      await writeFile(new URL(base + '.summary.json', auditDir), JSON.stringify(summary, null, 2));
      console.log(JSON.stringify({ device, scores, diagnostics: summary.failures.map(audit => audit.id) }));
    } finally {
      await chrome.kill();
    }
  }
} finally {
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
}
