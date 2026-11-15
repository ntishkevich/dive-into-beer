const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const runtime=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES||'C:/Users/HomePC/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {chromium}=require(path.join(runtime,'playwright'));
const root=path.resolve(__dirname,'..');
const url=pathToFileURL(path.join(root,'index.html')).href;
const expected=[
 ['start','start','Начало'],['map','start','Карта понятий'],
 ['history-old','history-old','Древность'],['history-new','history-old','крафту'],
 ['history-regional','history-old','Россия и Беларусь'],
 ['school-central','school-central','Германия'],['school-belgium','school-central','Бельгия'],
 ['school-islands','school-central','Ирландия'],['school-america','school-central','США'],
 ['school-russia','school-central','Россия'],['school-belarus','school-central','Беларусь'],
 ['hops','hops','IPA'],['sour','sour','Гозе'],['wild','sour','Ламбик'],
 ['lagers','lagers','Лагеры'],['yeasty','lagers','Пшеница'],['dark','lagers','Портер'],
 ['brew','brew','Пивоварение'],['label','label','Этикетки'],
 ['myths','myths','байки'],['myths-inspectors','myths','штаны'],
 ['myths-cities','myths','Пльзень'],['myths-culture','myths','Нинкаси'],
 ['myths-brief','myths','Короткие ответы'],['quick','myths','Шпаргалка'],
 ['practice','practice','Самопроверка'],['sources','sources','Источники']
];
function assert(ok,message){if(!ok)throw Error(message);}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1200,height:900}});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto(url);
 const numbering=await page.evaluate(()=>Array.from(document.querySelectorAll('.atlas-sidebar a')).map(link=>({menu:link.querySelector('span').textContent.trim(),sections:Array.from(document.querySelectorAll('.sheet[data-nav-group]')).filter(section=>section.id!=='start'&&section.dataset.navGroup===link.dataset.sectionLink).map(section=>({id:section.id,heading:section.querySelector('.eyebrow').textContent.trim().split(' / ')[0],footer:section.querySelector('.chapter-footer span:last-child')?.textContent.trim()}))})));
 numbering.forEach((chapter,i)=>{
  const menu=String(i+1).padStart(2,'0');assert(chapter.menu===menu,'Chapter numbers must be consecutive from 01');
  chapter.sections.forEach((section,j)=>{const number=menu+(chapter.sections.length>1?'.'+(j+1):'');assert(section.heading===number,'Menu/heading mismatch for '+section.id);assert(section.footer==='РАЗДЕЛ '+number,'Footer mismatch for '+section.id);});
 });
 assert(numbering.reduce((n,c)=>n+c.sections.length,0)===expected.length-1,'Some sections have no chapter number');
 const menuCopies=await page.evaluate(()=>['.header-index','.atlas-mobile-index'].map(selector=>Array.from(document.querySelectorAll(selector+' a')).map(a=>a.querySelector('span').textContent.trim())));
 assert(menuCopies.every(copy=>JSON.stringify(copy)===JSON.stringify(numbering.map(c=>c.menu))),'Mobile and desktop numbers differ');
 async function waitForSection(id){await page.waitForFunction(id=>document.querySelector('.topnav').dataset.currentSection===id,id);}
 async function scrollTo(id){
  await page.evaluate(id=>{const el=document.getElementById(id);const h=document.querySelector('.topnav').getBoundingClientRect().height;window.scrollTo({top:el.getBoundingClientRect().top+window.scrollY-h-20,behavior:'instant'});},id);
  await waitForSection(id);
 }
 const states=[];
 for(const [id,group,label] of expected){
  await scrollTo(id);
  const state=await page.evaluate(()=>({id:document.querySelector('.topnav').dataset.currentSection,active:Array.from(document.querySelectorAll('.atlas-sidebar a[aria-current]')).map(a=>a.getAttribute('href')),title:document.querySelector('[data-current-section-title]').textContent}));
  assert(state.active.length===1&&state.active[0]==='#'+(group==='start'?'map':group),'Wrong active group for '+id);
  assert(state.title.includes(label),'Wrong title for '+id);states.push(state);
 }
 // Cross the history/schools boundary in both directions by a few pixels.
 await page.evaluate(()=>{const nav=document.querySelector('.topnav');const el=document.getElementById('school-central');window.scrollTo({top:el.getBoundingClientRect().top+window.scrollY-nav.getBoundingClientRect().height-27,behavior:'instant'});});
 await waitForSection('history-regional');
 await page.evaluate(()=>window.scrollBy({top:6,behavior:'instant'}));await waitForSection('school-central');
 await page.evaluate(()=>window.scrollBy({top:-6,behavior:'instant'}));await waitForSection('history-regional');
 const layouts=[];
 for(const width of [320,360,768,1200]){
  await page.setViewportSize({width,height:900});
  if(width<=900){await page.locator('.header-index summary').click();await page.locator('.header-index a[href="#school-central"]').click();}
  else await page.locator('.atlas-sidebar a[href="#school-central"]').click();
  await waitForSection('school-central');
  const layout=await page.evaluate(()=>{const nav=document.querySelector('.topnav').getBoundingClientRect();const section=document.getElementById('school-central').getBoundingClientRect();const title=document.querySelector('[data-current-section-title]').getBoundingClientRect();return {width:innerWidth,documentWidth:document.documentElement.scrollWidth,headerHeight:nav.height,headerTop:nav.top,sectionTop:section.top,titleRight:title.right,titleBottom:title.bottom,headerBottom:nav.bottom};});
  assert(layout.documentWidth<=width+1,'Horizontal overflow at '+width);
  assert(layout.headerHeight<300,'Header too tall at '+width);
  assert(layout.sectionTop>=layout.headerBottom-1,'Anchor hidden by header at '+width);
  assert(layout.titleRight<=width&&layout.titleBottom<=layout.headerBottom,'Current section clipped at '+width);
  layouts.push(layout);
  if(width===360||width===1200)await page.screenshot({path:path.join(root,'tmp/navigation-'+width+'.png')});
 }
 await page.locator('.atlas-sidebar a[href="#hops"]').click();await waitForSection('hops');
 await page.locator('.atlas-sidebar a[href="#sour"]').click();await waitForSection('sour');
 await page.goBack();await waitForSection('hops');await page.goForward();await waitForSection('sour');
 await page.setViewportSize({width:360,height:900});
 await page.locator('.header-index summary').click();await page.keyboard.press('Escape');
 assert(await page.locator('.header-index').evaluate(el=>!el.open),'Escape did not close the menu');
 await page.goto(url+'#school-belgium');await waitForSection('school-belgium');
 const deepLink=await page.evaluate(()=>({headerBottom:document.querySelector('.topnav').getBoundingClientRect().bottom,sectionTop:document.getElementById('school-belgium').getBoundingClientRect().top}));
 assert(deepLink.sectionTop>=deepLink.headerBottom-1,'Deep link hidden by header');
 assert(!errors.length,'Browser errors: '+errors.join('; '));
 const report={sectionsChecked:states.length,numbering,boundaryBothDirections:true,layouts,deepLink,nativeHistory:true,mobileMenuEscape:true,errors};
 fs.writeFileSync(path.join(root,'tmp/navigation-check.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify(report));await browser.close();
})().catch(error=>{console.error(error);process.exitCode=1;});
