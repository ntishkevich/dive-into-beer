const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const d=JSON.parse(fs.readFileSync(path.join(root,'assets/beer-data.json'),'utf8'));
const css=fs.readFileSync(path.join(root,'assets/beer.css'),'utf8');
const layoutCss=fs.readFileSync(path.join(root,'assets/atlas-layout.css'),'utf8');
const js=fs.readFileSync(path.join(root,'assets/learning.js'),'utf8');
const navigationJs=fs.readFileSync(path.join(root,'assets/navigation.js'),'utf8');
const e=s=>String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
const chapters=JSON.parse(fs.readFileSync(path.join(root,'assets/atlas-chapters.json'),'utf8')).map((chapter,i)=>({...chapter,number:String(i+1).padStart(2,'0')}));
const sectionMeta=new Map(chapters.flatMap(chapter=>chapter.sections.map((section,i)=>[section.id,{...section,group:chapter.group,number:chapter.number+(chapter.sections.length>1?'.'+(i+1):'')}])));
const expectedSectionIds=[...d.pages.map(p=>p.id),'practice','sources'];
if(sectionMeta.size!==expectedSectionIds.length||Array.from(sectionMeta.keys()).join('|')!==expectedSectionIds.join('|'))throw Error('Chapter outline must contain every section exactly once and in reading order');
const numberedHeading=(id,title)=>sectionMeta.get(id).number+' / '+title.replace(/^\d+(?:\.\d+)*\s*\/\s*/,'');
const footer=id=>'<footer class="chapter-footer"><span>ПОГРУЖЕНИЕ В ПИВАС</span><span>РАЗДЕЛ '+sectionMeta.get(id).number+'</span></footer>';
const bySource=Object.fromEntries(d.sources.map(s=>[s.id,s]));
const sourceNumber = source => String(source.n).padStart(2, '0');
const sourcePopoverId = source => 'source-popover-' + source.id;

function sourceControl(source, markup, { label } = {}) {
  const ariaLabel = label ? ` aria-label="${e(label)}"` : '';
  const link = `<a class="source-fallback" href="${e(source.url)}"${ariaLabel}>${markup}</a>`;
  return link + `<button type="button" class="source-trigger" popovertarget="${e(sourcePopoverId(source))}" aria-haspopup="dialog"${ariaLabel}>${markup}</button>`;
}

function refs(ids) {
  if (!ids?.length) return '';
  const controls = ids.map(id => {
    const source = bySource[id];
    if (!source) throw Error(id);
    const number = `[${sourceNumber(source)}]`;
    const label = `${number} — Источник ${source.n}: ${source.title}`;
    return sourceControl(source, number, { label });
  });
  return '<div class="refs">Источники: ' + controls.join('') + '</div>';
}

function sourcePopovers() {
  return d.sources.map(source => {
    const id = e(sourcePopoverId(source));
    return `<dialog id="${id}" class="source-popover" popover="auto" aria-labelledby="${id}-title">
  <div class="source-popover-top">
    <span>Источник ${sourceNumber(source)}</span>
    <button type="button" popovertarget="${id}" popovertargetaction="hide" aria-label="Закрыть карточку источника" autofocus>×</button>
  </div>
  <h2 id="${id}-title">${e(source.title)}</h2>
  <p>${e(source.note)}</p>
  <div class="source-popover-links">
    <a href="${e(source.url)}" target="_blank" rel="noopener">Открыть в новой вкладке ↗</a>
    <a href="#source-${e(source.id)}">К записи в атласе</a>
  </div>
</dialog>`;
  }).join('\n');
}
const card=(s)=>`<article id="style-${s.id}" class="style-card" data-family="${e(s.family)}"><h3>${e(s.name)}</h3><div class="style-sub">${e(s.sub)}</div><div class="style-stats"><span><b>ABV</b> ${e(s.abv)}</span><span><b>IBU</b> ${e(s.ibu)}</span></div><p><b>Вкус</b>${e(s.taste)}</p><p><b>История</b>${e(s.origin)}</p><p><b>Отличие</b>${e(s.difference)}</p>${refs(s.refs)}</article>`;
const table=(head,rows)=>'<div class="table-wrap"><table><thead><tr>'+head.map(x=>'<th scope="col">'+e(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(x=>'<td>'+e(x)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
function block(b){let html='';switch(b.type){
 case'stories':html='<div class="history-stories">'+b.items.map(x=>`<article class="history-story" id="${e(x.id)}"><div class="story-kicker">${e(x.kicker)}</div><h3>${e(x.title)}</h3>${x.paragraphs.map(p=>'<p>'+e(p)+'</p>').join('')}${x.palate?'<p class="story-palate">'+e(x.palate)+'</p>':''}${refs(x.refs)}</article>`).join('')+'</div>';break;
 case'layers':html='<div class="layers">'+b.items.map(r=>`<div class="layer"><span>${e(r[0])}</span><b>${e(r[1])}</b><p>${e(r[2])}</p></div>`).join('')+'</div>';break;
 case'cards':html='<div class="cards">'+b.items.map(x=>`<article class="card"><h3>${e(x.title)}</h3><p>${e(x.text)}</p>${refs(x.refs)}</article>`).join('')+'</div>';break;
 case'axes':case'ingredients':html=`<div class="${b.type}">`+b.items.map(r=>`<div class="${b.type==='axes'?'axis':'ingredient'}"><b>${e(r[0])}</b><span>${e(r[1])}</span></div>`).join('')+'</div>';break;
 case'callout':html=`<aside class="callout"><div class="label">${e(b.label)}</div><p>${e(b.text)}</p>${refs(b.refs)}</aside>`;return html;
 case'timeline':html='<ol class="timeline">'+b.items.map(x=>`<li><div class="date">${e(x.date)}</div><div><h3>${e(x.title)}</h3><p>${e(x.text)}</p>${refs(x.refs)}</div></li>`).join('')+'</ol>';break;
 case'styles':html=`<div class="style-grid ${b.ids.length===3?'three':''}">`+b.ids.map(id=>card(d.styles.find(s=>s.id===id))).join('')+'</div>';break;
 case'table':html=table(b.head,b.rows);break;
 case'process':html='<div class="process">'+b.items.map(r=>`<div class="step"><b>${e(r[0])}</b><p>${e(r[1])}</p></div>`).join('')+'</div>';break;
 case'labels':html='<div class="labels">'+b.items.map(x=>`<article class="label-example"><div class="example-tag">Пример этикетки · вымышленное пиво</div><h3>${e(x.name)}</h3><p class="stats">${e(x.stats)}</p><p class="notes">${e(x.notes)}</p><p class="explain">${e(x.explain)}</p></article>`).join('')+'</div>';break;
 case'myths':html='<div class="myths">'+b.items.map(x=>`<article class="myth"><h3>${e(x.title)}</h3><p>${e(x.text)}</p>${refs(x.refs)}</article>`).join('')+'</div>';break;
 case'quicktable':html=table(['Стиль / направление','Характер','ABV: ориентир'],['helles','pils','apa','ipa','hazy','gose','gueuze','weiss','saison','stout','imperial'].map(id=>d.styles.find(s=>s.id===id)).map(s=>[s.name,s.taste,s.abv]));break;
 case'recall':html='<div class="recall"><h3>Три вопроса для самопроверки</h3>'+b.items.map(r=>`<details><summary>${e(r[0])}</summary><p>${e(r[1])}</p></details>`).join('')+'</div>';break;
 default:throw Error('Unknown block '+b.type);
 }return html+refs(b.refs);}
function glass(x,y,color,haze=false){return `<g transform="translate(${x} ${y})"><path d="M0 0H74L65 146Q37 156 9 146Z" fill="${color}"/><path d="M8 17L15 137" fill="none" stroke="#fffdf7" stroke-opacity=".36" stroke-width="4"/><path d="M0 0Q8 -16 18 -6Q26 -20 37 -7Q49 -21 58 -6Q69 -17 74 0V13H0Z" fill="#f5edda"/>${haze?'<path d="M5 48H70M7 61H68M9 75H66" stroke="#faebc4" stroke-opacity=".3" stroke-width="5"/>':''}<path d="M0 0L9 146Q37 156 65 146L74 0" fill="none" stroke="#fffdf7" stroke-width="2" stroke-opacity=".6"/></g>`;}
const coverGlasses = [
  ['Солод', 'lagers', 'к лагерам', '#d69a2c'],
  ['Хмель', 'hops', 'к IPA и APA', '#ddac54', true],
  ['Кислота', 'sour', 'к кислым стилям', '#a6516e'],
  ['Обжарка', 'dark', 'к портерам и стаутам', '#30251c'],
].map(([name, section, destination, color, haze]) => `<a class="cover-glass-link" href="#${section}" aria-label="${name}. Перейти ${destination}">
  <figure class="cover-glass">
    <svg class="cover-glass-drawing" viewBox="-2 -22 78 178" width="78" height="178" aria-hidden="true" focusable="false">${glass(0, 0, color, haze)}</svg>
    <figcaption>${name}</figcaption>
  </figure>
  <span class="cover-glass-arrow" aria-hidden="true">↘</span>
</a>`).join('');
const icon = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-56 -24 186 186">
    <rect x="-56" y="-24" width="186" height="186" rx="24" fill="#183b34"/>
    ${glass(0, 0, '#d69a2c')}
  </svg>`
);
const cover=`<section id="start" class="sheet cover"><div class="eyebrow">ВИЗУАЛЬНЫЙ АТЛАС ПИВА</div><div class="cover-grid"><div><h1>Погружение<br>в ПИВАС</h1><p class="lead">История, стили и вкус.<br>${e(d.subtitle)}</p></div><div class="cover-art" role="group" aria-label="Четыре характера пива: солод, хмель, кислотность и обжарка">${coverGlasses}</div></div><div class="cover-route"><div><b>История</b><span>От древних пайков до Hazy IPA</span></div><div><b>${d.styles.length} стиля и направления</b><span>От хеллеса до Hazy IPA</span></div><div><b>Как выбрать</b><span>Сравнения, факты и немного практики</span></div></div><div class="intro-links"><a href="#hops"><b>IPA / APA</b>Хмельный характер</a><a href="#sour"><b>Gose / Sour</b>Варианты кислотности</a><a href="#school-central"><b>Пивные школы</b>Страны и их истории</a><a href="#label"><b>Этикетки</b>Перевод сокращений</a><a href="#quick"><b>Шпаргалка</b>Ориентиры для меню</a></div></section>`;
const compareProfiles = Object.fromEntries(['apa', 'ipa', 'hazy', 'dipa'].map(id => {
  const { name, abv, ibu, taste, difference } = d.styles.find(style => style.id === id);
  return [id, { name, abv, ibu, taste, difference }];
}));
const compareButtons = Object.entries(compareProfiles)
  .map(([id, { name }]) => `<button type="button" data-style="${id}" aria-pressed="false">${e(name)}</button>`)
  .join('');
const compare=`<div id="style-compare" class="compare-block no-print"><h3>Сравнение хмелевых профилей</h3><p>Для сравнения выберите до двух стилей. При выборе третьего заменяется первый.</p><div class="compare-picker">${compareButtons}</div><div class="table-wrap" data-compare-output aria-live="polite"></div></div>`;
const compareData = JSON.stringify(compareProfiles).replaceAll('<', '\\u003c');
const questions=[
{q:'В Hazy IPA чувствуется манго, но в составе нет фруктов. Какое объяснение подходит?',choices:['Хмельная ароматика','Молочная кислотность','Солодовая карамель'],answer:0,explain:'Хмели могут создавать фруктовые ассоциации без добавления манго.'},
{q:'В одном меню есть Gose и Gueuze. Как правильно их различить?',choices:['Разные традиции','Одинаковые названия','Случайные опечатки'],answer:0,explain:'Gose связан с немецким пшеничным пивом, солью и кориандром; Gueuze — с купажом бельгийских ламбиков.'},
{q:'На этикетке написано DDH. О какой стороне пива прежде всего идёт речь?',choices:['Плотность пива','Охмеление пива','Крепость пива'],answer:1,explain:'DDH раскрывается как Double Dry Hopped и относится к холодному охмелению.'},
{q:'На столе тёмный Irish Stout и золотистый Tripel. Чем надёжнее проверить, какой крепче?',choices:['Оттенком пива','Плотностью пены','Значением ABV'],answer:2,explain:'Цвет не даёт надёжной оценки крепости. У классического Tripel она часто выше, чем у Irish Stout.'}
];
const quizHtml=questions.map((x,i)=>`<div class="quiz" data-quiz data-answer="${x.answer}" data-explain="${e(x.explain)}"><h3>${i+1}. ${e(x.q)}</h3><div class="quiz-options">${x.choices.map((c,j)=>`<button type="button" data-choice="${j}">${e(c)}</button>`).join('')}</div><p class="quiz-feedback" aria-live="polite"></p></div>`).join('');
const practice=`<section id="practice" class="sheet"><div class="eyebrow">${e(numberedHeading('practice','САМОПРОВЕРКА · 3 МИНУТЫ'))}</div><h2>Четыре вопроса о пиве</h2><p class="lead">Чем отличаются похожие названия и что скрывается за сокращениями? После выбора ответа появится короткое объяснение.</p>${quizHtml}<p class="reading-note">Основные различия собраны в <a href="#quick">шпаргалке для меню</a>, а подробности о сокращениях — в разделе <a href="#label">об этикетках</a>.</p>${footer('practice')}</section>`;
const content=d.pages.map(p=>`<section id="${p.id}" class="sheet"><div class="eyebrow">${e(numberedHeading(p.id,p.eyebrow))}</div><h2>${e(p.title)}</h2><p class="lead">${e(p.lead)}</p>${p.id==='hops'?'<p class="reading-note">Значения ABV и IBU ниже — ориентиры BJCP 2021 для указанных профилей. Конкретное пиво может выходить за эти диапазоны, а сами диапазоны могут пересекаться.</p>':''}${p.blocks.map(block).join('')}${p.id==='hops'?compare:''}${footer(p.id)}</section>`).join('');
const sourceEntries = d.sources.map(source => {
  const title = `<span class="source-number">${sourceNumber(source)}</span> ${e(source.title)}`;
  return `<article class="source" id="source-${e(source.id)}"><b>${sourceControl(source, title)}</b><p>${e(source.note)}</p><small>${e(new URL(source.url).hostname)}</small></article>`;
}).join('');
const sourcesHtml=`<section id="sources" class="sheet"><div class="eyebrow">${e(numberedHeading('sources','ДЛЯ ДАЛЬНЕЙШЕГО ЧТЕНИЯ'))}</div><h2>Источники и пояснения</h2><p class="lead">Основа описаний — BJCP Beer Style Guidelines 2021. Для современных направлений дополнительно использованы Brewers Association 2026 и объяснения пивоварен.</p><p class="reading-note">Справочники описывают типичный профиль; названия в меню не всегда совпадают с конкурсными категориями. Легенды и исторические реконструкции отмечены отдельно. Вкусовые сравнения помогают представить пиво и не заменяют перечень ингредиентов.</p><div class="source-grid">${sourceEntries}</div>${footer('sources')}</section>`;
const readingSections=Object.fromEntries([['start',['start','Начало']],...Array.from(sectionMeta,([id,meta])=>[id,[meta.group,meta.readingTitle]])]);
function annotateSections(body){return body.replace(/<section id="([^"]+)" class="sheet([^"]*)">/g,(markup,id,classes)=>{const info=readingSections[id];if(!info)throw Error('Missing navigation label: '+id);return `<section id="${e(id)}" class="sheet${classes}" data-nav-group="${e(info[0])}" data-reading-title="${e(info[1])}" tabindex="-1">`;});}
const outline=chapters.map(chapter=>[chapter.sections[0].id,chapter.group,chapter.title,chapter.number]);
const outlineLinks=()=>outline.map(([id,group,title,number])=>'<a href="#'+e(id)+'" data-section-link="'+e(group)+'"><span>'+number+'</span>'+e(title)+'</a>').join('');
const nav='<nav class="topnav" aria-label="Навигация по атласу"><div class="nav-main"><a class="brand" href="#start" data-section-link="start">ПОГРУЖЕНИЕ В ПИВАС</a><details class="header-index"><summary>Содержание</summary><nav aria-label="Быстрый переход по атласу">'+outlineLinks()+'</nav></details></div><div class="reading-location"><span class="reading-location-label">Сейчас читаете</span><span class="reading-title" data-current-section-title role="status" aria-live="polite" aria-atomic="true">Начало</span></div><div class="reading-progress" aria-hidden="true"><span></span></div></nav>';
const sidebar='<aside class="atlas-sidebar" aria-label="Оглавление атласа"><p class="index-label">Путеводитель по атласу</p><nav aria-label="Главы атласа">'+outlineLinks()+'</nav></aside>';
const mobileIndex='<details class="atlas-mobile-index"><summary>Содержание атласа</summary><nav aria-label="Содержание на небольшом экране">'+outlineLinks()+'</nav></details>';
function doc(body) {
  const styles = `<style>\n${css}\n${layoutCss}\n</style>`;
  const skipLink = '<a class="skip-link" href="#map">Перейти к содержанию</a>';
  const data = `<script type="application/json" id="compare-data">${compareData}</script>`;
  // Embed the module so it also runs when the page is opened from disk.
  const script = js + '\n' + navigationJs;
  return `<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="История пива и понятная карта стилей: IPA, APA, Hazy, Gose, sour, лагеры и стауты"><title>${e(d.title)}</title><link rel="icon" type="image/svg+xml" href="${icon}">${styles}</head><body class="atlas-page">${skipLink}${annotateSections(body)}${data}
<script type="module">${script}</script>
</body></html>`;
}
const atlasBody=nav+'<main id="atlas-content">'+cover+'<div class="atlas-layout">'+sidebar+'<div class="atlas-content">'+mobileIndex+content+practice+sourcesHtml+'</div></div></main>'+sourcePopovers();
const indexPath = path.join(root, 'index.html');
fs.writeFileSync(indexPath, doc(atlasBody));
fs.writeFileSync(path.join(root, '.nojekyll'), '');
console.log(JSON.stringify({ index: indexPath, styles: d.styles.length, sources: d.sources.length }));
