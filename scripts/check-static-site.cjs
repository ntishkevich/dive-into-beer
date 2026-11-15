const fs=require('node:fs');const path=require('node:path');const http=require('node:http');const assert=require('node:assert/strict');
const runtime=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES||'C:/Users/HomePC/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {chromium}=require(path.join(runtime,'playwright'));const root=path.resolve(__dirname,'..');
const expectedSources=require('../assets/beer-data.json').sources.length;
(async()=>{
 const html=fs.readFileSync(path.join(root,'index.html'));
 assert(html.equals(fs.readFileSync(path.join(root,'output/beer-atlas.html'))),'Standalone and index differ');
 const server=http.createServer((req,res)=>{
  if(['/beer-project/','/beer-project/index.html'].includes(req.url.split('?')[0])){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html);}
  else{res.writeHead(404);res.end('Not found');}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1200,height:1000}});const errors=[],assets=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('request',r=>{if(['script','stylesheet','image','font','fetch','xhr'].includes(r.resourceType()))assets.push(r.url());});
  const base='http://127.0.0.1:'+server.address().port+'/beer-project/';
  await page.goto(base+'#map');await page.waitForFunction(()=>document.querySelector('.topnav').dataset.currentSection==='map');
  const state=await page.evaluate(()=>({title:document.title,h1:document.querySelector('h1').innerText.replace(/\s+/g,' ').trim(),charset:document.characterSet,main:document.querySelectorAll('main').length,styles:document.querySelectorAll('.style-card').length,sources:document.querySelectorAll('.source').length,text:document.body.innerText,localLinks:[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(h=>!h.startsWith('#')&&!/^https?:/.test(h))}));
  assert.equal(state.title,'Погружение в ПИВАС');assert.equal(state.h1,'Погружение в ПИВАС');assert.equal(state.charset,'UTF-8');assert.equal(state.main,1);assert.equal(state.styles,22);assert.equal(state.sources,expectedSources);
  assert.equal(await page.locator('.atlas-sidebar').count(),1);assert.equal(await page.locator('.prototype-switcher,[data-variant-step],.reading-chapter').count(),0);
  assert(!html.toString().includes('data-prototype')&&!html.toString().includes('data-variant'),'Prototype controls leaked into production');
  assert(!/Русский язык|Источники проверены|преподавател|в чате|Твоя цель|Сначала раздели\s|\uFFFD/i.test(state.text),'Private lesson copy remains');
  assert.equal(state.localLinks.length,0);assert.equal(assets.length,0);assert.equal(errors.length,0);
  await page.locator('.brand').click();await page.waitForFunction(()=>document.querySelector('.topnav').dataset.currentSection==='start');
  await page.screenshot({path:path.join(root,'tmp/public-desktop.png')});
  await page.setViewportSize({width:360,height:900});await page.goto(base+'#map');await page.waitForFunction(()=>document.querySelector('.topnav').dataset.currentSection==='map');
  await page.screenshot({path:path.join(root,'tmp/public-mobile.png')});
  await page.setViewportSize({width:320,height:480});
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto(base+'#history-old');
  const historyCitations = page.locator('#history-old .source-trigger');
  const openedSource = page.getByRole('dialog', {name: 'Stanford / Liu et al., 2018'});
  await historyCitations.first().press('Enter');
  assert(await openedSource.isVisible());
  await page.keyboard.press('Tab');
  assert(await openedSource.getByRole('link', {name: /Открыть в новой вкладке/}).evaluate(el => document.activeElement === el));
  await page.keyboard.press('Tab');
  assert(await openedSource.getByRole('link', {name: 'К записи в атласе'}).evaluate(el => document.activeElement === el));
  await page.keyboard.press('Tab');
  await openedSource.waitFor({state:'hidden',timeout:3000});
  assert(await historyCitations.nth(1).evaluate(el => document.activeElement === el));
  const staticPage=await browser.newPage({javaScriptEnabled:false});await staticPage.goto(base);
  assert.equal(await staticPage.locator('.style-card').count(),22);assert.equal(await staticPage.locator('.source').count(),expectedSources);
  assert.equal(await staticPage.locator('.atlas-sidebar a').count(),11);
  const glass = staticPage.getByRole('link', {name: 'Хмель. Перейти к IPA и APA'});
  await glass.press('Enter');
  assert.equal(new URL(staticPage.url()).hash, '#hops');
  await staticPage.goto(base + '#history-old');
  const citation = staticPage.locator('#history-old .source-trigger').first();
  await citation.press('Enter');
  const popover = staticPage.getByRole('dialog', {name: 'Stanford / Liu et al., 2018'});
  assert(await popover.isVisible());
  assert.equal(await popover.getByRole('link', {name: 'К записи в атласе'}).getAttribute('href'), '#source-arch');
  await staticPage.keyboard.press('Escape');
  assert(!(await popover.isVisible()));
  assert(await citation.evaluate(el => document.activeElement === el));
  const entries = await staticPage.locator('#sources .source').evaluateAll(sources => sources.map(source => {
   const button = source.querySelector('.source-trigger');
   const dialog = document.getElementById(button?.getAttribute('popovertarget'));
   return {
    id: source.id,
    correctDialog: dialog?.id === source.id.replace(/^source-/, 'source-popover-'),
    originalLink: dialog?.querySelector('a[target="_blank"]')?.href,
    fallbackLink: source.querySelector('.source-fallback')?.href,
   };
  }));
  assert.equal(entries.length, state.sources);
  for (const {id, correctDialog, originalLink, fallbackLink} of entries) {
   assert(correctDialog && originalLink && originalLink === fallbackLink, 'Invalid source popup for ' + id);
  }
  const bibliographyButton = staticPage.getByRole('button', {name: '01 Stanford / Liu et al., 2018'});
  await bibliographyButton.press('Enter');
  assert(await popover.isVisible());
  await staticPage.keyboard.press('Escape');
  assert(!(await popover.isVisible()));
  assert(await bibliographyButton.evaluate(el => document.activeElement === el));
  const report={projectSubpath:true,title:state.title,profiles:state.styles,sources:state.sources,externalAssetRequests:assets,privateLessonCopy:false,prototypeControls:false,staticOutline:true,readableWithoutJavaScript:true,coverLinksWithoutJavaScript:true,sourcePopoverWithoutJavaScript:true,bibliographyPopovers:entries.length,errors};
  fs.writeFileSync(path.join(root,'tmp/static-site-check.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
