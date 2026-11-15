from pathlib import Path
import json, html, re
from urllib.parse import urlparse
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable, KeepTogether, KeepInFrame
from reportlab.lib.pagesizes import A4
from reportlab.platypus import HRFlowable

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'assets/beer-data.json').read_text(encoding='utf-8'))
CHAPTERS = json.loads((ROOT/'assets/atlas-chapters.json').read_text(encoding='utf-8'))
SECTION_NUMBERS = {
 section['id']: f'{chapter_number:02}' + (f'.{section_number}' if len(chapter['sections']) > 1 else '')
 for chapter_number, chapter in enumerate(CHAPTERS, 1)
 for section_number, section in enumerate(chapter['sections'], 1)
}
OUT=ROOT/'output'/'beer-atlas.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Text','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Text-Bold','C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Text-Italic','C:/Windows/Fonts/ariali.ttf'))
pdfmetrics.registerFont(TTFont('Display','C:/Windows/Fonts/georgia.ttf'))
pdfmetrics.registerFontFamily('Text',normal='Text',bold='Text-Bold',italic='Text-Italic',boldItalic='Text-Bold')
PAPER=colors.HexColor('#faf6ed'); INK=colors.HexColor('#183b34'); MUTED=colors.HexColor('#59665d'); LINE=colors.HexColor('#d9d7c8'); AMBER=colors.HexColor('#b35b16'); HOP=colors.HexColor('#527142'); SOUR=colors.HexColor('#8b4667'); SOFT=colors.HexColor('#eee8d9')
PW,PH=A4; M=37; W=PW-M*2
S={
 'body':ParagraphStyle('body',fontName='Text',fontSize=9.05,leading=12.2,textColor=INK,spaceAfter=5),
 'lead':ParagraphStyle('lead',fontName='Text',fontSize=10.2,leading=14,textColor=MUTED,spaceAfter=13),
 'title':ParagraphStyle('title',fontName='Display',fontSize=27,leading=30,textColor=INK,spaceAfter=11),
 'eyebrow':ParagraphStyle('eyebrow',fontName='Text-Bold',fontSize=7.3,leading=10.5,textColor=AMBER,spaceAfter=12),
 'h3':ParagraphStyle('h3',fontName='Display',fontSize=16,leading=18,textColor=INK,spaceAfter=8),
 'h4':ParagraphStyle('h4',fontName='Display',fontSize=13.6,leading=16,textColor=INK,spaceAfter=7),
 'sub':ParagraphStyle('sub',fontName='Text',fontSize=7.6,leading=10,textColor=MUTED,spaceAfter=8),
 'stats':ParagraphStyle('stats',fontName='Text-Bold',fontSize=8,leading=11,textColor=AMBER,spaceAfter=8),
 'ref':ParagraphStyle('ref',fontName='Text',fontSize=6.7,leading=9,textColor=MUTED,spaceAfter=6),
 'table':ParagraphStyle('table',fontName='Text',fontSize=8.2,leading=11,textColor=INK),
 'th':ParagraphStyle('th',fontName='Text-Bold',fontSize=7.2,leading=9.5,textColor=INK),
 'small':ParagraphStyle('small',fontName='Text',fontSize=8.1,leading=10.8,textColor=MUTED,spaceAfter=7),
 'date':ParagraphStyle('date',fontName='Display',fontSize=13.6,leading=16,textColor=AMBER,spaceAfter=5),
 'answer':ParagraphStyle('answer',fontName='Text',fontSize=8.2,leading=11,textColor=MUTED,spaceAfter=8),
 'story':ParagraphStyle('story',fontName='Text',fontSize=9.6,leading=13.6,textColor=INK,spaceAfter=8),
 'palate':ParagraphStyle('palate',fontName='Text-Italic',fontSize=8.7,leading=12,textColor=HOP,spaceAfter=6),
}
SRC={s['id']:s for s in D['sources']}
ST={s['id']:s for s in D['styles']}
def esc(s):
 return html.escape(str(s)).replace('−','-').replace('–','-').replace('—','-').replace('\u2011','-')
def p(s,style='body',raw=False):return Paragraph(s if raw else esc(s),S[style])
def refs(ids):
 if not ids:return []
 text='Источники: '+' '.join('<a href="'+esc(SRC[k]['url'])+'" color="#59665d">['+str(SRC[k]['n']).zfill(2)+']</a>' for k in ids)
 return [p(text,'ref',True)]
def styled_table(rows,widths,header=False,soft=False):
 t=Table(rows,colWidths=widths,hAlign='LEFT')
 commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]
 if header:commands += [('LINEBELOW',(0,0),(-1,0),.8,INK),('LINEBELOW',(0,1),(-1,-1),.3,LINE)]
 if soft:commands += [('BACKGROUND',(0,0),(-1,-1),SOFT)]
 t.setStyle(TableStyle(commands));return t
def pairs(cells,soft=False,lines=False):
 result=[]
 for i in range(0,len(cells),2):
  group=cells[i:i+2]
  widths=[(W-14)/2,14,(W-14)/2] if len(group)==2 else [W]
  row=[group[0],[],group[1]] if len(group)==2 else [group[0]]
  t=styled_table([row],widths)
  commands=[]
  if soft:
   commands+=[('BACKGROUND',(0,0),(0,0),SOFT)]
   if len(group)==2:commands+=[('BACKGROUND',(2,0),(2,0),SOFT)]
  if lines:
   commands+=[('LINEABOVE',(0,0),(0,0),1.7,HOP)]
   if len(group)==2:commands+=[('LINEABOVE',(2,0),(2,0),1.7,HOP)]
  t.setStyle(TableStyle(commands));result.extend([t,Spacer(1,7)])
 return result
def style_cell(s):
 out=[p(s['name'],'h3'),p(s['sub'],'sub'),p('ABV '+s['abv']+'   |   IBU '+s['ibu'],'stats')]
 for key,label in [('taste','Вкус'),('origin','История'),('difference','Отличие')]:out.append(p('<b>'+label+'.</b> '+esc(s[key]),raw=True))
 return out+refs(s['refs'])
def generic_cell(x,head='h4'):return [p(x['title'],head),p(x['text'])]+refs(x.get('refs'))
def block(b):
 out=[]; t=b['type']
 if t=='stories':
  for x in b['items']:
   out.extend([HRFlowable(width='100%',thickness=.5,color=LINE),Spacer(1,11),p(x['kicker'],'eyebrow'),p(x['title'],'h3')])
   out.extend(p(text,'story') for text in x['paragraphs'])
   if x.get('palate'):out.append(p(x['palate'],'palate'))
   out.extend(refs(x['refs'])+[Spacer(1,12)])
 elif t=='layers':
  rows=[[p(r[0],'small'),p(r[1],'h4'),p(r[2])] for r in b['items']]
  out=[styled_table(rows,[77,155,W-232]),Spacer(1,12)]
 elif t=='cards':out=pairs([generic_cell(x) for x in b['items']],soft=True)
 elif t in ('axes','ingredients'):
  cells=[[p(r[0],'h4'),p(r[1],'small')] for r in b['items']]
  out=[styled_table([cells],[W/len(cells)]*len(cells)),Spacer(1,10)]
 elif t=='callout':
  cell=[p(b['label'].upper(),'eyebrow'),p(b['text'])]+refs(b.get('refs'))
  t1=styled_table([[cell]],[W],soft=True);t1.setStyle(TableStyle([('LINEBEFORE',(0,0),(0,0),2.6,HOP)]))
  return [Spacer(1,8),t1,Spacer(1,8)]
 elif t=='timeline':
  rows=[[p(x['date'],'date'),[p(x['title'],'h4'),p(x['text'])]+refs(x.get('refs'))] for x in b['items']]
  t1=styled_table(rows,[111,W-111]);t1.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-1),.35,LINE)]));out=[t1,Spacer(1,10)]
 elif t=='styles':out=pairs([style_cell(ST[x]) for x in b['ids']],lines=True)
 elif t=='table':
  rows=[[p(x,'th') for x in b['head']]]+[[p(x,'table') for x in row] for row in b['rows']]
  cols=len(b['head']); widths=[W*.22,W*.78] if cols==2 else [W*.22,W*.39,W*.39]
  out=[styled_table(rows,widths,header=True),Spacer(1,10)]
 elif t=='process':
  cells=[[p(str(i+1).zfill(2),'date'),p(r[0],'h4'),p(r[1])] for i,r in enumerate(b['items'])]
  out=[]
  for i in range(0,len(cells),3):
   group=cells[i:i+3]
   row=[]; widths=[]
   for j,cell in enumerate(group):
    if j:row.append([]);widths.append(9)
    row.append(cell);widths.append((W-9*(len(group)-1))/len(group))
   out.extend([styled_table([row],widths),Spacer(1,6)])
 elif t=='labels':
  cells=[]
  for x in b['items']:
   cells.append([p('ПРИМЕР ЭТИКЕТКИ: ВЫМЫШЛЕННОЕ ПИВО','sub'),p(x['name'],'h3'),p(x['stats'],'stats'),p(x['notes'],'small'),p(x['explain'])])
  out=pairs(cells,soft=True)
 elif t=='myths':out=pairs([generic_cell(x) for x in b['items']])
 elif t=='quicktable':
  ids=['helles','pils','apa','ipa','hazy','gose','gueuze','weiss','saison','stout','imperial']
  rows=[[p(x,'th') for x in ['Стиль / направление','Характер','ABV: ориентир']]]
  rows += [[p(ST[x]['name'],'table'),p(ST[x]['taste'],'table'),p(ST[x]['abv'],'table')] for x in ids]
  out=[styled_table(rows,[W*.23,W*.55,W*.22],header=True),Spacer(1,16)]
 elif t=='recall':
  out=[p('Три вопроса для самопроверки','h3')]
  for r in b['items']:out.extend([p(r[0],'body'),p('Подсказка: '+r[1],'answer')])
 else:raise ValueError(t)
 return out+refs(b.get('refs'))

class Cover(Flowable):
 def __init__(self):Flowable.__init__(self);self.width=W;self.height=PH-M*2-4
 def draw(self):
  c=self.canv
  c.setFillColor(colors.HexColor('#e6b970'));c.setFont('Text-Bold',9);c.drawString(2,731,'ВИЗУАЛЬНЫЙ АТЛАС ПИВА')
  c.setFillColor(PAPER);c.setFont('Display',53);c.drawString(0,654,'Погружение');c.setFont('Display',59);c.drawString(0,585,'в ПИВАС')
  c.setFont('Text',15);c.drawString(2,541,'История, стили и вкус.');c.setFont('Text',11);c.setFillColor(colors.HexColor('#d2dace'));c.drawString(2,518,'Как появились пивные стили, чем они отличаются');c.drawString(2,500,'и откуда берутся знакомые вкусы.')
  labels=['СОЛОД','ХМЕЛЬ','КИСЛОТА','ОБЖАРКА']; fills=['#d69a2c','#ddac54','#a6516e','#30251c']
  for i in range(4):
   x=22+i*130;y=281
   c.setFillColor(colors.HexColor(fills[i]));q=c.beginPath();q.moveTo(x,y+144);q.lineTo(x+79,y+144);q.lineTo(x+68,y+1);q.curveTo(x+49,y-6,x+30,y-6,x+11,y+1);q.close();c.drawPath(q,fill=1,stroke=0)
   c.setStrokeColor(colors.HexColor('#f7edda'));c.setLineWidth(1);c.drawPath(q,fill=0,stroke=1)
   c.setFillColor(colors.HexColor('#f7edda'));c.roundRect(x,y+132,79,21,8,stroke=0,fill=1)
   c.setFillColor(colors.HexColor('#e6b970'));c.setFont('Text-Bold',8);c.drawCentredString(x+40,y-27,labels[i])
  c.setStrokeColor(colors.HexColor('#6c8475'));c.setLineWidth(.6);c.line(0,213,W,213)
  for i,(title,detail) in enumerate([('История','От древних пайков до IPA'),(str(len(D['styles']))+' стиля\nи направления','От хеллеса до Hazy IPA'),('Как выбрать','Сравнения, факты и практика')]):
   x=i*(W/3);c.setFillColor(colors.HexColor('#e6b970'));c.setFont('Display',19)
   for line_index,line in enumerate(title.split('\n')):c.drawString(x,171-line_index*22,line)
   c.setFillColor(colors.HexColor('#d2dace'));c.setFont('Text',8);c.drawString(x,129,detail)

def on_page(c,doc):
 c.saveState()
 if doc.page==1:
  c.setFillColor(INK);c.rect(0,0,PW,PH,fill=1,stroke=0)
 else:
  c.setFillColor(PAPER);c.rect(0,0,PW,PH,fill=1,stroke=0)
  c.setStrokeColor(LINE);c.setLineWidth(.4);c.line(M,29,PW-M,29)
  c.setFont('Text',7);c.setFillColor(MUTED);c.drawString(M,17,'ПОГРУЖЕНИЕ В ПИВАС  /  ВИЗУАЛЬНЫЙ АТЛАС');c.drawRightString(PW-M,17,str(doc.page).zfill(2))
 c.restoreState()
doc=BaseDocTemplate(str(OUT),pagesize=A4,rightMargin=M,leftMargin=M,topMargin=M,bottomMargin=40,title=D['title']+' - визуальный атлас',author='Погружение в ПИВАС',subject='История пива, стили и чтение меню')
frame=Frame(M,40,W,PH-M-40,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='normal')
doc.addPageTemplates([PageTemplate(id='all',frames=[frame],onPage=on_page)])
story=[Cover(),PageBreak()]
fit_groups=[]
for page in D['pages']:
 eyebrow = re.sub(r'^\d+(?:\.\d+)*\s*/\s*', '', page['eyebrow'])
 group=[p(f"{SECTION_NUMBERS[page['id']]} / {eyebrow}",'eyebrow'),p(page['title'],'title'),p(page['lead'],'lead')]
 if page['id']=='hops':group.append(p('Числа ниже - диапазоны BJCP 2021 для указанных профилей, а не обязательные пределы коммерческих версий. Пересечение диапазонов нормально.','small'))
 for b in page['blocks']:group.extend(block(b))
 fitted=KeepInFrame(W,PH-M-40,group,mode='shrink',hAlign='LEFT',vAlign='TOP')
 fit_groups.append((page['id'],fitted));story.append(fitted)
 story.append(PageBreak())
source_page_count=(len(D['sources'])+16)//17
for idx in range(source_page_count):
 group=[p(f"{SECTION_NUMBERS['sources']} / ИСТОЧНИКИ · {idx+1} ИЗ {source_page_count}",'eyebrow'),p('Источники и пояснения','title')]
 group.append(p('BJCP 2021 задаёт ориентиры профилей; Brewers Association 2026 дополняет современную карту. Названия на рынке могут использоваться свободнее. Ссылки кликабельны.','lead'))
 cells=[]
 for s in D['sources'][idx*17:(idx+1)*17]:
  title='<font color="#b35b16">'+str(s['n']).zfill(2)+'</font>  <a href="'+esc(s['url'])+'"><b>'+esc(s['title'])+'</b></a>'
  cells.append([p(title,'body',True),p(s['note'],'small'),p(urlparse(s['url']).hostname,'ref')])
 group.extend(pairs(cells))
 fitted=KeepInFrame(W,PH-M-40,group,mode='shrink',hAlign='LEFT',vAlign='TOP')
 fit_groups.append(('sources'+str(idx+1),fitted));story.append(fitted)
 if idx<source_page_count-1:story.append(PageBreak())
doc.build(story)
from pypdf import PdfReader
r=PdfReader(str(OUT));summary=[]
for i,page in enumerate(r.pages):
 text=page.extract_text() or ''
 summary.append({'page':i+1,'chars':len(text),'start':text[:95].replace('\n',' / ')})
qa={'file':str(OUT),'pages':len(r.pages),'fit_scales':{key:round(getattr(item,'_scale',1),3) for key,item in fit_groups},'page_summary':summary}
qa_path = ROOT / 'tmp' / 'pdf-check.json'
qa_path.parent.mkdir(parents=True, exist_ok=True)
qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'pages':qa['pages'],'fit_scales':qa['fit_scales'],'page_chars':[x['chars'] for x in summary]},ensure_ascii=True))
