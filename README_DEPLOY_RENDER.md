# نشر إنجاز Flask على Render

## التشغيل المحلي
python run.py

## Render
- ارفع المشروع إلى GitHub.
- في Render اختر New > Web Service.
- اربط مستودع GitHub.
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn wsgi:app
- Python: 3.13.7
- أضف SECRET_KEY أو استخدم render.yaml الذي يولده تلقائياً.

## ملاحظات
- الموقع Flask كما هو، وليس Blogger.
- حد رفع الملفات 100MB في التطبيق.
- أدوات PDF التي تعتمد على LibreOffice تحتاج تثبيت LibreOffice على بيئة الاستضافة؛ أما الأدوات المبنية على ReportLab/pypdf/PyMuPDF فتستخدم المتطلبات الحالية.
