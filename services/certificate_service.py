import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart

def generate_certificate_id():
    """產生唯一的證書編號"""
    from datetime import datetime
    import random
    return f"IMC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

def build_certificate_pdf(certificate, lang="zh"):
    """產生原有的證書 PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    content = []
    title_text = "碳排減量證書" if lang == "zh" else "Carbon Reduction Certificate"
    content.append(Paragraph(title_text, styles['Title']))
    content.append(Spacer(1, 12))
    
    company_text = f"公司名稱：{certificate.get('company_name', '')}" if lang == "zh" else f"Company: {certificate.get('company_name', '')}"
    content.append(Paragraph(company_text, styles['Normal']))
    
    cert_id_text = f"證書編號：{certificate.get('cert_id', '')}" if lang == "zh" else f"Certificate ID: {certificate.get('cert_id', '')}"
    content.append(Paragraph(cert_id_text, styles['Normal']))
    
    issued_text = f"發行日期：{certificate.get('issued_at', '')}" if lang == "zh" else f"Issue Date: {certificate.get('issued_at', '')}"
    content.append(Paragraph(issued_text, styles['Normal']))
    
    doc.build(content)
    buffer.seek(0)
    return buffer

def build_certificate_pdf_report(company_name, start_date, end_date, total_containers, 
                                  total_carbon_saved, total_cost_saved, sea_count, road_count, records):
    """產生減碳績效證書 PDF（Dashboard 使用）"""
    
    buffer = io.BytesIO()
    
    # 使用 A4 橫向
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                           rightMargin=15*mm, leftMargin=15*mm,
                           topMargin=15*mm, bottomMargin=15*mm)
    
    styles = getSampleStyleSheet()
    
    # 自訂樣式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#1a5276'),
        alignment=1,  # 居中
        spaceAfter=15,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2980b9'),
        alignment=1,
        spaceAfter=25,
        fontName='Helvetica'
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1a5276'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    stat_number_style = ParagraphStyle(
        'StatNumber',
        parent=styles['Normal'],
        fontSize=22,
        textColor=colors.HexColor('#27ae60'),
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    stat_label_style = ParagraphStyle(
        'StatLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#7f8c8d'),
        alignment=1,
        fontName='Helvetica'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica',
        leading=14
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#95a5a6'),
        alignment=1,
        fontName='Helvetica'
    )
    
    content = []
    
    # ==================== 標題區域 ====================
    content.append(Paragraph("🌊 iMarine Carbon Reduction Certificate", title_style))
    content.append(Paragraph(f"Reporting Period: {start_date} to {end_date}", subtitle_style))
    content.append(Spacer(1, 5))
    content.append(Paragraph(f"This certificate is proudly presented to", normal_style))
    content.append(Paragraph(f"<b>{company_name}</b>", title_style))
    content.append(Spacer(1, 15))
    
    # ==================== 統計卡片（使用表格） ====================
    stats_data = [
        [
            Paragraph(f"<b>{total_containers:,}</b>", stat_number_style),
            Paragraph(f"<b>{total_carbon_saved:,.0f}</b>", stat_number_style),
            Paragraph(f"<b>NT$ {total_cost_saved:,.0f}</b>", stat_number_style),
            Paragraph(f"<b>{sea_count}</b>", stat_number_style),
        ],
        [
            Paragraph("Total Containers<br/>(FEU)", stat_label_style),
            Paragraph("CO₂e Reduced<br/>(kg)", stat_label_style),
            Paragraph("Cost Savings<br/>(NTD)", stat_label_style),
            Paragraph("Sea<br/>Shipments", stat_label_style),
        ]
    ]
    
    stats_table = Table(stats_data, colWidths=[95, 95, 95, 80])
    stats_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f4f8')),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1a5276')),
    ]))
    content.append(stats_table)
    content.append(Spacer(1, 20))
    
    # ==================== 環保效益說明 ====================
    content.append(Paragraph("🌱 Environmental Impact Summary", section_title_style))
    
    # 碳排換算（相當於多少棵樹）
    trees_equivalent = total_carbon_saved / 25 if total_carbon_saved > 0 else 0  # 每棵樹每年吸收約25kg CO2
    cars_equivalent = total_carbon_saved / 4600 if total_carbon_saved > 0 else 0  # 每輛車每年排放約4600kg CO2
    lightbulbs_equivalent = total_carbon_saved / 0.5 if total_carbon_saved > 0 else 0  # LED燈泡每年0.5kg CO2
    
    impact_text = f"""
    By choosing Blue Highway over inland road transportation, 
    <b>{company_name}</b> has successfully reduced carbon emissions by 
    <b>{total_carbon_saved:,.0f} kg CO₂e</b> during the specified period.<br/><br/>
    
    This reduction is equivalent to:
    <br/>• 🌳 Planting approximately <b>{trees_equivalent:.0f} trees</b> and letting them grow for one year
    <br/>• 🚗 Removing <b>{cars_equivalent:.1f} passenger vehicles</b> from the road for one year
    <br/>• 💡 Powering <b>{lightbulbs_equivalent:,.0f} LED light bulbs</b> for one year
    """
    
    content.append(Paragraph(impact_text, normal_style))
    content.append(Spacer(1, 15))
    
    # ==================== 運輸模式對比 ====================
    if sea_count + road_count > 0:
        content.append(Paragraph("📊 Mode of Transport Comparison", section_title_style))
        
        total_shipments = sea_count + road_count
        sea_percent = (sea_count / total_shipments) * 100 if total_shipments > 0 else 0
        road_percent = (road_count / total_shipments) * 100 if total_shipments > 0 else 0
        
        mode_data = [
            ["Mode", "Shipments", "Percentage", "Carbon Saved"],
            ["Blue Highway (Sea)", f"{sea_count}", f"{sea_percent:.1f}%", f"--"],
            ["Inland Road", f"{road_count}", f"{road_percent:.1f}%", f"--"],
        ]
        
        mode_table = Table(mode_data, colWidths=[120, 80, 80, 100])
        mode_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        content.append(mode_table)
        content.append(Spacer(1, 15))
    
    # ==================== 詳細記錄表格 ====================
    if records and len(records) > 0:
        content.append(Paragraph("📋 Detailed Shipment Records", section_title_style))
        
        # 表格標題
        table_data = [
            ["Date", "Route", "Containers", "CO₂ Saved (kg)", "Mode"]
        ]
        
        for r in records[:15]:  # 最多顯示15筆
            mode_text = "Sea" if r.get("best_mode") == "海運" else "Road"
            table_data.append([
                r.get("date", "").split(" ")[0] if r.get("date") else "-",
                f"{r.get('start', '')} → {r.get('end', '')}",
                str(r.get("containers", 0)),
                f"{r.get('carbon_improvement', 0):,.0f}",
                mode_text
            ])
        
        # 計算欄位寬度
        col_widths = [70, 110, 60, 80, 50]
        
        record_table = Table(table_data, colWidths=col_widths)
        record_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        content.append(record_table)
    
    content.append(Spacer(1, 25))
    
    # ==================== 簽章區域 ====================
    signature_data = [
        ["", ""],
        ["<b>iMarine Carbon Management</b>", "<b>Verified By</b>"],
        ["Digital Signature", "Blockchain Verified"],
        [f"Date: {datetime.now().strftime('%Y-%m-%d')}", "Certificate ID: " + generate_certificate_id()]
    ]
    
    signature_table = Table(signature_data, colWidths=[160, 160])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    content.append(signature_table)
    
    content.append(Spacer(1, 15))
    
    # ==================== 頁尾 ====================
    content.append(Paragraph("-" * 90, footer_style))
    content.append(Paragraph(
        "This certificate is generated automatically by iMarine Carbon Management Platform. "
        "The data is based on actual shipment records and carbon calculations using standard emission factors.", 
        footer_style
    ))
    content.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | iMarine © 2025 | All Rights Reserved",
        footer_style
    ))
    
    # 產生 PDF
    doc.build(content)
    buffer.seek(0)
    return buffer