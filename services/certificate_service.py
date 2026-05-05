import random
from datetime import datetime
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

def generate_certificate_id():
    return f"CC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

def build_certificate_pdf(certificate, lang="en"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    title = "Carbon Emission Reduction Certificate"
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=22,
        textColor=colors.HexColor('#03045e'), alignment=1, spaceAfter=30)
    cert_style = ParagraphStyle('Cert', parent=styles['Normal'], fontSize=12,
        textColor=colors.HexColor('#023e8a'), spaceAfter=12)

    record = certificate.get("record", {})
    content = [
        Paragraph(title, title_style),
        Paragraph(f"Certificate ID: {certificate['cert_id']}", cert_style),
        Paragraph(f"Issue Date: {certificate.get('issued_at', datetime.now().strftime('%Y-%m-%d'))}", cert_style),
        Spacer(1, 20),
        Paragraph(f"Company: {certificate['company_name']}", cert_style),
        Paragraph(f"Route: {record.get('start','')} → {record.get('end','')}", cert_style),
        Paragraph(f"Containers: {record.get('containers','')} {record.get('unit','FEU')}", cert_style),
        Spacer(1, 20),
        Paragraph("Calculation Basis:", cert_style),
        Paragraph("• ISO 14064 Principles", cert_style),
        Paragraph("• GLEC Framework", cert_style),
        Paragraph("• EU ETS Carbon Pricing", cert_style),
        Spacer(1, 20),
        Paragraph(f"Carbon Saved: {record.get('ci',0):.2f} kg CO2e", cert_style),
        Paragraph(f"Reduction Rate: {record.get('rp',0)}%", cert_style),
        Paragraph(f"Carbon Credit Value: NT$ {record.get('cc',0):,.2f}", cert_style),
        Spacer(1, 30),
        Paragraph("Hereby Certified", cert_style),
        Paragraph("iMarine Carbon Management Center", cert_style),
    ]

    doc.build(content)
    buffer.seek(0)
    return buffer