from __future__ import annotations
import csv, io, json, re, shutil, subprocess, tempfile, zipfile
from pathlib import Path
from html.parser import HTMLParser
from flask import send_file
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE = Path(__file__).resolve().parent
FONT_CANDIDATES = [BASE/'static/fonts/Amiri-Regular.ttf', Path('C:/Windows/Fonts/arial.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
BOLD_CANDIDATES = [BASE/'static/fonts/Amiri-Bold.ttf', Path('C:/Windows/Fonts/arialbd.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]

def _pick(items): return next((p for p in items if p.exists()), None)

def register_arabic_font():
    regular, bold = _pick(FONT_CANDIDATES), _pick(BOLD_CANDIDATES)
    if regular:
        if 'EngazFont' not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont('EngazFont', str(regular)))
        if bold and 'EngazBold' not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont('EngazBold', str(bold)))
        return 'EngazFont', 'EngazBold' if bold else 'EngazFont'
    return 'Helvetica', 'Helvetica-Bold'

def arabic(text):
    text = str(text or '')
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text

def safe_name(name, default='engaz.pdf'):
    name = Path(name or default).name
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in name) or default

def response(data, filename='engaz.pdf', mimetype='application/pdf'):
    return send_file(io.BytesIO(data), mimetype=mimetype, as_attachment=True, download_name=safe_name(filename), max_age=0)

def _draw_wrapped(c, text, font, size, x_right, y, width_chars=82, leading=19):
    c.setFont(font, size)
    for raw in str(text or '').splitlines() or ['']:
        if not raw:
            y -= leading
            continue
        line=''
        for word in raw.split():
            test=(line+' '+word).strip()
            if len(test)>width_chars and line:
                c.drawRightString(x_right,y,arabic(line)); y-=leading; line=word
            else: line=test
        c.drawRightString(x_right,y,arabic(line)); y-=leading
    return y

def text_pdf(text, title='إنجاز'):
    font,bold=register_arabic_font(); out=io.BytesIO(); c=canvas.Canvas(out,pagesize=A4); W,H=A4
    c.setTitle(str(title)); c.setFont(bold,18); c.drawCentredString(W/2,H-42,arabic(title)); y=H-78
    for raw in str(text or '').splitlines() or ['']:
        if y<55: c.showPage(); c.setFont(font,12); y=H-45
        # preserve long strings as chunks
        y=_draw_wrapped(c, raw, font, 12, W-42, y)
        if y<55: c.showPage(); c.setFont(font,12); y=H-45
    c.save(); return out.getvalue()

def images_pdf(files, page='a4'):
    sizes={'a4':A4,'a5':(420.94,595.28),'letter':(612,792)}; W,H=sizes.get(page,A4)
    out=io.BytesIO(); c=canvas.Canvas(out,pagesize=(W,H)); count=0
    for storage in files:
        storage.stream.seek(0); img=ImageReader(storage.stream); iw,ih=img.getSize()
        if not iw or not ih: continue
        scale=min((W-48)/iw,(H-48)/ih); dw,dh=iw*scale,ih*scale
        c.drawImage(img,(W-dw)/2,(H-dh)/2,width=dw,height=dh,preserveAspectRatio=True,mask='auto'); c.showPage(); count+=1
    if not count: raise ValueError('لم يتم التعرف على أي صورة صالحة.')
    c.save(); return out.getvalue()

def _reader(f):
    f.stream.seek(0); return PdfReader(f.stream)

def merge_pdfs(files):
    w=PdfWriter(); count=0
    for f in files:
        r=_reader(f)
        if r.is_encrypted:
            try: r.decrypt('')
            except Exception: raise ValueError('يوجد ملف PDF محمي بكلمة مرور.')
        for p in r.pages: w.add_page(p); count+=1
    if not count: raise ValueError('لا توجد صفحات صالحة للدمج.')
    out=io.BytesIO(); w.write(out); return out.getvalue()

def _parse_pages(raw,total):
    result=[]
    for part in str(raw or '').replace('،',',').split(','):
        part=part.strip()
        if not part: continue
        if '-' in part:
            a,b=map(int,part.split('-',1)); a,b=sorted((a,b)); result.extend(range(a,b+1))
        else: result.append(int(part))
    result=[n for n in result if 1<=n<=total]
    return list(dict.fromkeys(result))

def split_pdf(file,pages):
    r=_reader(file); w=PdfWriter(); nums=_parse_pages(pages,len(r.pages))
    if not nums: raise ValueError(f'أرقام الصفحات غير صحيحة. الملف يحتوي على {len(r.pages)} صفحة.')
    for n in nums: w.add_page(r.pages[n-1])
    out=io.BytesIO(); w.write(out); return out.getvalue()

def rotate_pdf(file,degrees):
    r=_reader(file); w=PdfWriter()
    for p in r.pages: p.rotate(degrees); w.add_page(p)
    out=io.BytesIO(); w.write(out); return out.getvalue()

class TextExtractor(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,data): self.parts.append(data)
    def text(self): return re.sub(r'\n\s*\n+', '\n\n', '\n'.join(self.parts)).strip()

def html_to_pdf(html,title='إنجاز'): p=TextExtractor(); p.feed(str(html)); return text_pdf(p.text(),title)

def table_pdf(rows,title='إنجاز'):
    font,bold=register_arabic_font(); out=io.BytesIO(); c=canvas.Canvas(out,pagesize=landscape(A4)); W,H=landscape(A4)
    rows=[list(map(str,r)) for r in rows if r]
    if not rows: raise ValueError('لا توجد بيانات.')
    cols=max(len(r) for r in rows); rows=[r+['']*(cols-len(r)) for r in rows]; widths=[(W-40)/cols]*cols; y=H-48; rh=24
    c.setTitle(str(title)); c.setFont(bold,16); c.drawCentredString(W/2,H-25,arabic(title))
    for ri,row in enumerate(rows):
        if y<45: c.showPage(); y=H-35
        c.setFont(bold if ri==0 else font,8); x=20
        for ci,val in enumerate(row):
            c.rect(x,y-rh,widths[ci],rh); c.drawCentredString(x+widths[ci]/2,y-16,arabic(val[:55])); x+=widths[ci]
        y-=rh
    c.save(); return out.getvalue()

def csv_to_pdf(raw,title='إنجاز — CSV'): return table_pdf(list(csv.reader(io.StringIO(raw))),title)
def json_to_pdf(raw,title='إنجاز — JSON'): return text_pdf(json.dumps(json.loads(raw),ensure_ascii=False,indent=2),title)

def pdf_to_images_zip(file, fmt='png', dpi=150):
    import fitz
    data=file.read(); doc=fitz.open(stream=data,filetype='pdf')
    fmt='jpg' if fmt.lower() in ('jpg','jpeg') else 'png'; dpi=max(72,min(int(dpi),300)); scale=dpi/72; mat=fitz.Matrix(scale,scale)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=mat,alpha=False)
            ext='jpg' if fmt=='jpg' else 'png'; z.writestr(f'page-{i+1:03d}.{ext}',pix.tobytes(ext))
    return out.getvalue()

def convert_office(file_storage):
    exe=shutil.which('libreoffice') or shutil.which('soffice')
    if not exe: raise RuntimeError('تحويل Word/Excel/PowerPoint يحتاج LibreOffice مثبتًا على جهاز السيرفر.')
    suffix=Path(file_storage.filename or '').suffix.lower()
    if suffix not in {'.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.odp'}: raise ValueError('صيغة الملف غير مدعومة.')
    with tempfile.TemporaryDirectory() as td:
        src=Path(td)/safe_name(file_storage.filename,'input'+suffix); file_storage.save(src)
        r=subprocess.run([exe,'--headless','--convert-to','pdf','--outdir',td,str(src)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=120)
        pdf=src.with_suffix('.pdf')
        if r.returncode!=0 or not pdf.exists(): raise RuntimeError((r.stderr or r.stdout or 'فشل LibreOffice في التحويل.').strip())
        return pdf.read_bytes()
