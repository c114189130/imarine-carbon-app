import random
from datetime import datetime
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 註冊中文字型
try:
    pdfmetrics.registerFont(TTFont('MicrosoftJhengHei', 'msjh.ttf'))
    FONT_NAME = 'MicrosoftJhengHei'
except:
    FONT_NAME = 'Helvetica'


def generate_certificate_id() -> str:
    return f"CC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


def build_certificate_pdf(certificate: dict, lang: str = "zh") -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    if lang == "zh":
        title = "🌱 碳排放減量證明書"
        title_text = "碳排放減量證明書"
        cert_label = "證書編號"
        date_label = "核發日期"
        company_label = "公司名稱"
        route_label = "運輸路線"
        containers_label = "貨櫃數量"
        reduction_label = "減碳量"
        reduction_rate_label = "減碳比例"
        basis_title = "📊 計算依據"
        basis_items = [
            "• ISO 14064 原則",
            "• GLEC Framework（物流碳排）",
            "• DEFRA emission factors",
            "• 台灣環境部碳費參考",
        ]
        footer = "特此證明"
        issuer = "iMarine 智慧海運碳排認證中心"
    else:
        title = "🌱 Carbon Emission Reduction Certificate"
        title_text = "Carbon Emission Reduction Certificate"
        cert_label = "Certificate ID"
        date_label = "Issue Date"
        company_label = "Company Name"
        route_label = "Route"
        containers_label = "Containers (FEU)"
        reduction_label = "Carbon Saved"
        reduction_rate_label = "Reduction Rate"
        basis_title = "📊 Calculation Basis"
        basis_items = [
            "• ISO 14064",
            "• GLEC Framework",
            "• DEFRA emission factors",
            "• Taiwan EPA Carbon Fee",
        ]
        footer = "Hereby Certified"
        issuer = "iMarine Carbon Management Center"

    title_style = ParagraphStyle(
        'Title', parent=styles['Title'], fontSize=24,
        textColor=colors.HexColor('#03045e'), alignment=1, spaceAfter=30, fontName=FONT_NAME
    )
    cert_style = ParagraphStyle(
        'Cert', parent=styles['Normal'], fontSize=12,
        textColor=colors.HexColor('#023e8a'), spaceAfter=12, fontName=FONT_NAME
    )

    record = certificate.get("record", {})
    content = [
        Paragraph(title, title_style),
        Paragraph(f"{cert_label}：{certificate['cert_id']}", cert_style),
        Paragraph(f"{date_label}：{certificate.get('issued_at', datetime.now().strftime('%Y-%m-%d'))}", cert_style),
        Spacer(1, 20),
        Paragraph(f"{company_label}：{certificate['company_name']}", cert_style),
        Paragraph(f"{route_label}：{record.get('start', '')} → {record.get('end', '')}", cert_style),
        Paragraph(f"{containers_label}：{record.get('containers', 0)} FEU", cert_style),
        Spacer(1, 20),
        Paragraph(basis_title, cert_style),
    ]
    for item in basis_items:
        content.append(Paragraph(item, cert_style))

    content.extend([
        Spacer(1, 20),
        Paragraph(f"{reduction_label}：{record.get('carbon_improvement', 0):.2f} kg CO2e", cert_style),
        Paragraph(f"{reduction_rate_label}：{record.get('reduction_pct', 0)}%", cert_style),
        Spacer(1, 30),
        Paragraph(footer, cert_style),
        Paragraph(issuer, cert_style),
    ])

    doc.build(content)
    buffer.seek(0)
    return buffer