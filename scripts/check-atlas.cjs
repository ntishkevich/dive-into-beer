const fs=require('node:fs');const path=require('node:path');const {pathToFileURL}=require('node:url');
const runtime=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES||'C:/Users/HomePC/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {chromium}=require(path.join(runtime,'playwright'));
const root=path.resolve(__dirname,'..');
const expected=JSON.parse(fs.readFileSync(path.join(root,'assets/beer-data.json'),'utf8'));
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1200,height:900},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(path.join(root,'output/beer-atlas.html')).href);
 const structure=await page.evaluate(()=>({chapters:document.querySelectorAll('.sheet').length,profiles:document.querySelectorAll('.style-card').length,sources:document.querySelectorAll('.source').length,brokenAnchors:Array.from(document.querySelectorAll('a[href^="#"]')).map(a=>a.getAttribute('href')).filter(h=>!document.getElementById(h.slice(1))),externalAssets:document.querySelectorAll('script[src],link[rel="stylesheet"],img[src]').length}));
 const layout=[];
 for(const width of [320,360,768,1200]){
  await page.setViewportSize({width,height:900});
  const state=await page.evaluate(()=>{
   const h=document.querySelector('.cover h1');const r=document.createRange();r.selectNodeContents(h);
   const coverRouteFits=Array.from(document.querySelectorAll('.cover-route b,.cover-route span')).every(el=>{
    const cell=el.parentElement.getBoundingClientRect();const text=document.createRange();text.selectNodeContents(el);
    return Array.from(text.getClientRects()).every(rect=>rect.left>=cell.left-1&&rect.right<=cell.right+1);
   });
   return {width:innerWidth,documentWidth:document.documentElement.scrollWidth,coverHeadingWidth:r.getBoundingClientRect().width,coverAvailable:h.clientWidth,coverRouteFits};
  });
  layout.push(state);
 }
 await page.setViewportSize({width:1200,height:1000});
 await page.locator('.cover').screenshot({path:path.join(root,'tmp/cover-browser.png')});
 await page.locator('#hops').screenshot({path:path.join(root,'tmp/hops-browser.png')});
 await page.locator('#school-central').screenshot({path:path.join(root,'tmp/schools-central-browser.png')});
 await page.locator('#school-belgium').screenshot({path:path.join(root,'tmp/schools-belgium-browser.png')});
 await page.locator('#style-compare button[data-style="dipa"]').click();
 const comparison=await page.locator('[data-compare-output]').innerText();
 await page.locator('[data-quiz]').first().locator('button[data-choice="0"]').click();
 const feedback=await page.locator('[data-quiz]').first().locator('.quiz-feedback').innerText();
 const feedbackClass=await page.locator('[data-quiz]').first().locator('.quiz-feedback').getAttribute('class');
 await page.locator('[data-quiz]').nth(1).locator('button[data-choice="2"]').click();
 const wrongFeedbackClass=await page.locator('[data-quiz]').nth(1).locator('.quiz-feedback').getAttribute('class');
 await page.setViewportSize({width:360,height:900});await page.locator('#hops').screenshot({path:path.join(root,'tmp/hops-mobile.png')});
 await page.goto(pathToFileURL(path.join(root,'lessons/0001-reading-beer-menu.html')).href);
 const lessonOk=await page.locator('[data-quiz]').count()===4 && await page.locator('.quiz-options button').count()===12;
 await page.locator('[data-quiz]').nth(2).locator('button[data-choice="1"]').click();
 const lessonFeedback=await page.locator('[data-quiz]').nth(2).locator('.quiz-feedback').innerText();
 const result={structure,layout,comparisonUpdated:comparison.toLowerCase().includes('double ipa'),correctFeedback:feedback,correctClass:feedbackClass,wrongClass:wrongFeedbackClass,lessonOk,lessonFeedback,errors};
 fs.writeFileSync(path.join(root,'tmp/browser-check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 await browser.close();
 if(errors.length||structure.brokenAnchors.length||structure.profiles!==22||structure.sources!==expected.sources.length||layout.some(x=>x.documentWidth>x.width+1||x.coverHeadingWidth>x.coverAvailable+1||!x.coverRouteFits)||!result.comparisonUpdated||!lessonOk||!feedbackClass.includes('good')||!wrongFeedbackClass.includes('bad'))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
