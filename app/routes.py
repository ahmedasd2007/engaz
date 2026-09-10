from datetime import datetime
from pathlib import Path
from html import escape
from flask import Blueprint, render_template, request, jsonify, Response, abort, redirect, url_for, current_app
from .data.catalog import CATEGORIES, TOOLS

bp = Blueprint('main', __name__)


def normalize(value):
    value = (value or '').strip().lower()
    trans = str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ى':'ي','ة':'ه','ؤ':'و','ئ':'ي'})
    return ' '.join(value.translate(trans).split())


def search_tools(q):
    qn = normalize(q)
    if not qn:
        return TOOLS
    tokens = qn.split()
    scored = []
    for t in TOOLS:
        hay = normalize(' '.join([t[0], t[1], t[2], t[4], t[5]]))
        score = 0
        if qn in normalize(t[2]): score += 100
        if qn in normalize(t[4]): score += 45
        if qn == normalize(t[0]): score += 80
        score += sum(8 for token in tokens if token in hay)
        if score:
            scored.append((score, t))
    scored.sort(key=lambda x: (-x[0], normalize(x[1][2])))
    return [t for _, t in scored]


@bp.context_processor
def inject_globals():
    return {
        'year': datetime.now().year,
        'site_name': 'إنجاز',
        'site_description': 'منصة عربية ذكية لإنجاز الحسابات والتحويلات وأدوات النصوص والبرمجة والصور بسرعة.',
    }


@bp.get('/')
def home():
    return render_template('index.html', categories=CATEGORIES, tools=TOOLS)


@bp.get('/category/<slug>')
def category(slug):
    category_data = next((x for x in CATEGORIES if x[0] == slug), None)
    if slug == 'files' and category_data is None:
        category_data = ('files', '📁', 'الملفات وPDF', 'تحويل ودمج وتقسيم ومعالجة الملفات وملفات PDF')
    if not category_data:
        abort(404)
    tools = [t for t in TOOLS if t[1] == slug]
    return render_template('category.html', category=category_data, tools=tools)


@bp.get('/tool/<slug>')
def tool(slug):
    tool_data = next((x for x in TOOLS if x[0] == slug), None)
    if not tool_data:
        abort(404)
    category_data = next((x for x in CATEGORIES if x[0] == tool_data[1]), None)
    related = [t for t in TOOLS if t[1] == tool_data[1] and t[0] != slug][:6]
    return render_template('tool.html', tool=tool_data, category=category_data, related=related)


@bp.get('/search')
def search():
    q = request.args.get('q', '').strip()
    return render_template('search.html', q=q, results=search_tools(q))


@bp.get('/api/tools')
def api_tools():
    q = request.args.get('q', '').strip()
    results = search_tools(q)
    return jsonify([
        {
            'slug': t[0], 'category': t[1], 'name': t[2],
            'icon': t[3], 'description': t[4], 'type': t[5]
        } for t in results
    ])


@bp.get('/sitemap.xml')
def sitemap():
    base = request.url_root.rstrip('/')
    urls = [base + '/']
    urls += [base + '/category/' + c[0] for c in CATEGORIES]
    urls += [base + '/tool/' + t[0] for t in TOOLS]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        xml.append(f'<url><loc>{escape(url)}</loc></url>')
    xml.append('</urlset>')
    return Response(''.join(xml), mimetype='application/xml')


@bp.get('/robots.txt')
def robots():
    base = request.url_root.rstrip('/')
    return Response(
        f'User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {base}/sitemap.xml\n',
        mimetype='text/plain'
    )


@bp.get('/about')
def about():
    return render_template(
        'static_page.html', title='عن إنجاز',
        body='إنجاز منصة عربية مجانية تجمع الأدوات اليومية في مكان واحد، من الحاسبات والمحوّلات إلى النصوص والبرمجة والمال والتاريخ والصور.'
    )


@bp.get('/privacy')
def privacy():
    return render_template(
        'static_page.html', title='سياسة الخصوصية',
        body='نص تمهيدي لسياسة الخصوصية. قبل الإطلاق التجاري يجب تخصيص السياسة وفق الاستضافة والتحليلات والإعلانات وأي خدمات خارجية يستخدمها الموقع.'
    )


@bp.get('/terms')
def terms():
    return render_template(
        'static_page.html', title='شروط الاستخدام',
        body='نص تمهيدي لشروط الاستخدام. يجب مراجعته وتخصيصه قبل الإطلاق التجاري بما يتوافق مع طبيعة الخدمات والقوانين المطبقة.'
    )


@bp.errorhandler(404)
def not_found(error):
    return render_template('static_page.html', title='الصفحة غير موجودة', body='عذرًا، الصفحة التي تبحث عنها غير موجودة. يمكنك العودة للرئيسية واستكشاف الأدوات.'), 404


@bp.errorhandler(500)
def server_error(error):
    return render_template('static_page.html', title='حدث خطأ', body='حدث خطأ غير متوقع. حاول تحديث الصفحة أو العودة للرئيسية.'), 500


@bp.get('/files-center')
def files_category():
    category_data = ('files', '📁', 'الملفات وPDF', 'تحويل ودمج وتقسيم ومعالجة الملفات وملفات PDF')
    tools = [t for t in TOOLS if t[1] == 'files']
    return render_template('category.html', category=category_data, tools=tools)


@bp.get("/files")
def files_center():
    return redirect(url_for("main.pdf_center"))


@bp.get("/pdf")
def pdf_center():
    kind = request.args.get("kind", "images-to-pdf").strip().lower()
    allowed = {"images-to-pdf","text-to-pdf","html-to-pdf","csv-to-pdf","json-to-pdf","merge","split","rotate"}
    if kind not in allowed:
        kind = "images-to-pdf"
    return render_template("pdf_center.html", kind=kind)


# ========================= PDF API =========================
from .pdf_service import text_pdf, images_pdf, merge_pdfs, split_pdf, rotate_pdf, table_pdf, csv_to_pdf, json_to_pdf, html_to_pdf, convert_office, pdf_to_images_zip, response

@bp.get('/api/pdf/health')
def pdf_health():
    return jsonify({'ok': True, 'service': 'Engaz PDF', 'message': 'محرك PDF يعمل.'})

def _pdf_error(message, code=400):
    return jsonify({'ok': False, 'error': str(message)}), code

def _pages(raw):
    result=[]
    for part in str(raw or '').replace('،',',').split(','):
        part=part.strip()
        if not part: continue
        if '-' in part:
            a,b=part.split('-',1); a,b=int(a),int(b)
            if a>b: a,b=b,a
            result.extend(range(a,b+1))
        else: result.append(int(part))
    return result

@bp.post('/api/pdf/text')
def pdf_text_api():
    text=request.form.get('text','')
    if not text.strip(): return _pdf_error('اكتب النص أولاً.')
    try: return response(text_pdf(text,request.form.get('title') or 'إنجاز — ملف PDF'),'engaz-text.pdf')
    except Exception as e: return _pdf_error(f'فشل إنشاء PDF: {e}',500)

@bp.post('/api/pdf/images')
def pdf_images_api():
    request_id = request.headers.get('X-Engaz-Request') or request.form.get('_request_id') or 'no-request-id'
    files=[f for f in request.files.getlist('files') if f and f.filename]
    current_app.logger.info('PDF images request id=%s files=%s content_length=%s', request_id, len(files), request.content_length)
    if not files:
        current_app.logger.warning('PDF images EMPTY request id=%s content_type=%s', request_id, request.content_type)
        return _pdf_error('لم تصل أي صور إلى الخادم. اختر الصور ثم حاول مرة أخرى.')
    if len(files)>50:
        return _pdf_error('الحد الأقصى 50 صورة.')
    allowed={'.jpg','.jpeg','.png','.webp'}
    bad=[f.filename for f in files if Path(f.filename).suffix.lower() not in allowed]
    if bad:
        return _pdf_error('يسمح فقط بصور JPG وPNG وWEBP.')
    try:
        return response(images_pdf(files),'engaz-images.pdf')
    except Exception as e:
        current_app.logger.exception('PDF images failed: %s', e)
        return _pdf_error(f'فشل إنشاء PDF من الصور: {e}',500)

@bp.post('/api/pdf/merge')
def pdf_merge_api():
    files=[f for f in request.files.getlist('files') if f and f.filename]
    if len(files)<2: return _pdf_error('اختر ملفي PDF على الأقل.')
    try: return response(merge_pdfs(files),'engaz-merged.pdf')
    except Exception as e: return _pdf_error(f'فشل دمج PDF: {e}',400)

@bp.post('/api/pdf/split')
def pdf_split_api():
    f=request.files.get('file')
    if not f or not f.filename: return _pdf_error('اختر ملف PDF.')
    try: return response(split_pdf(f,_pages(request.form.get('pages'))),'engaz-pages.pdf')
    except Exception as e: return _pdf_error(f'فشل استخراج الصفحات: {e}',400)

@bp.post('/api/pdf/rotate')
def pdf_rotate_api():
    f=request.files.get('file')
    if not f or not f.filename: return _pdf_error('اختر ملف PDF.')
    try:
        d=int(request.form.get('degrees','90'))
        if d not in (90,180,270): raise ValueError('الزاوية يجب أن تكون 90 أو 180 أو 270.')
        return response(rotate_pdf(f,d),'engaz-rotated.pdf')
    except Exception as e: return _pdf_error(f'فشل تدوير PDF: {e}',400)

@bp.post('/api/pdf/table')
def pdf_table_api():
    raw=request.form.get('data','').strip()
    if not raw: return _pdf_error('أدخل بيانات الجدول.')
    try: return response(table_pdf([x.split(',') for x in raw.splitlines()],request.form.get('title') or 'إنجاز — تقرير'),'engaz-table.pdf')
    except Exception as e: return _pdf_error(f'فشل إنشاء الجدول: {e}',500)

@bp.post('/api/pdf/csv')
def pdf_csv_api():
    raw=request.form.get('data','')
    if not raw.strip(): return _pdf_error('أدخل بيانات CSV أولاً.')
    try: return response(csv_to_pdf(raw,request.form.get('title') or 'إنجاز — CSV'),'engaz-csv.pdf')
    except Exception as e: return _pdf_error(f'فشل تحويل CSV: {e}',500)

@bp.post('/api/pdf/json')
def pdf_json_api():
    raw=request.form.get('data','')
    if not raw.strip(): return _pdf_error('أدخل JSON أولاً.')
    try: return response(json_to_pdf(raw,request.form.get('title') or 'إنجاز — JSON'),'engaz-json.pdf')
    except Exception as e: return _pdf_error(f'فشل تحويل JSON: {e}',500)

@bp.post('/api/pdf/html')
def pdf_html_api():
    raw=request.form.get('data','')
    if not raw.strip(): return _pdf_error('أدخل HTML أولاً.')
    try: return response(html_to_pdf(raw,request.form.get('title') or 'إنجاز — HTML'),'engaz-html.pdf')
    except Exception as e: return _pdf_error(f'فشل تحويل HTML: {e}',500)

@bp.post('/api/pdf/to-images')
def pdf_to_images_api():
    f=request.files.get('file')
    if not f or not f.filename: return _pdf_error('اختر ملف PDF.')
    try:
        data=pdf_to_images_zip(f, request.form.get('format','png'), request.form.get('dpi','150'))
        return response(data,'engaz-pdf-images.zip','application/zip')
    except Exception as e: return _pdf_error(f'فشل تحويل PDF إلى صور: {e}',400)

@bp.post('/api/pdf/office')
def pdf_office_api():
    f=request.files.get('file')
    if not f or not f.filename: return _pdf_error('اختر ملف Word أو Excel أو PowerPoint.')
    try: return response(convert_office(f),Path(f.filename).stem+'.pdf')
    except Exception as e: return _pdf_error(str(e),400)
