import io
import re
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import A5, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from database import IST, get_account_name

def format_date_str(d):
    """Universal DD-MM-YYYY date formatter for strings, dates, and timestamps"""
    if d is None or str(d).strip() in ('', 'None', 'NaT', 'nan'):
        return ""
    if hasattr(d, 'strftime'):
        try:
            return d.strftime('%d-%m-%Y')
        except Exception:
            pass
    s = str(d).strip()
    if re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', s):
        try:
            s_clean = s[:10].replace('/', '-')
            return datetime.strptime(s_clean, '%Y-%m-%d').strftime('%d-%m-%Y')
        except Exception:
            return s
    return s

try:
    import streamlit as st
    cache_data = st.cache_data(show_spinner=False)
except Exception:
    def cache_data(f):
        return f

@cache_data
def create_pdf_report(title, df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                           rightMargin=10*mm, leftMargin=10*mm, 
                           topMargin=15*mm, bottomMargin=15*mm)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Company Header Style
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    
    subheader_style = ParagraphStyle(
        'SubheaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1,
        spaceAfter=2,
        textColor=colors.HexColor('#333333')
    )
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    # Company Header
    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Paragraph("6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", subheader_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Ph: 0471-2994535", subheader_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 8))
    
    if not df.empty:
        # Clean data for PDF
        cleaned_data = []
        columns = list(df.columns)
        
        for row in df.values:
            cleaned_row = []
            for col_idx, val in enumerate(row):
                col_name = columns[col_idx].lower()
                
                # Format float/numeric amounts nicely with commas
                if isinstance(val, (int, float)):
                    if any(k in col_name for k in ['debit', 'credit', 'balance', 'amount', 'total', 'interest', 'rs', '₹']):
                        if val == 0:
                            val_str = "0.00"
                        else:
                            val_str = f"{val:,.2f}"
                    else:
                        val_str = str(val)
                else:
                    val_str = str(val) if val is not None else ""
                    val_str = format_date_str(val_str)
                
                val_str = val_str.replace('₹', 'Rs.')
                ascii_val = val_str.encode('ascii', 'ignore').decode('ascii')
                
                # Wrap long text columns in Paragraph to enable auto line-wrapping in ReportLab
                if col_name in ['particulars/narration', 'particulars', 'narration', 'description', 'name', 'account name', 'account head', 'head of account']:
                    cell_text_style = ParagraphStyle(
                        f'CellText_{col_idx}',
                        parent=styles['Normal'],
                        fontSize=7,
                        fontName='Helvetica',
                        leading=9
                    )
                    cleaned_row.append(Paragraph(ascii_val, cell_text_style))
                else:
                    cleaned_row.append(ascii_val)
            cleaned_data.append(cleaned_row)
        
        # Calculate optimal column widths based on column names
        available_width = 262  # mm total printable width for landscape A4
        num_cols = len(columns)
        
        # Specific optimized widths for standard 7-8 column financial books
        col_widths = []
        for col in columns:
            c_low = col.lower()
            if 'date' in c_low:
                col_widths.append(22)
            elif any(k in c_low for k in ['voucher', 'tx id', 'id', 'vr no']):
                col_widths.append(28)
            elif 'account head' in c_low or 'head of account' in c_low:
                col_widths.append(48)
            elif 'particulars' in c_low or 'description' in c_low:
                col_widths.append(60)
            elif any(k in c_low for k in ['debit', 'credit', 'balance', 'amount', 'total', 'interest', 'rs', '₹']):
                col_widths.append(24)
            elif 'narration' in c_low:
                col_widths.append(32)
            elif 'bank' in c_low:
                col_widths.append(30)
            else:
                col_widths.append(30)
                
        total_w = sum(col_widths)
        if total_w != available_width:
            scale = available_width / total_w
            col_widths = [w * scale for w in col_widths]
        
        col_widths_pt = [w * mm for w in col_widths]
        
        table_data = [columns] + cleaned_data
        t = Table(table_data, colWidths=col_widths_pt, repeatRows=1)
        
        # Build precise alignment and styling rules
        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d5dd')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3.5),
        ]
        
        # Alternating row background colors
        for r_idx in range(1, len(table_data)):
            bg = colors.HexColor('#ffffff') if r_idx % 2 == 1 else colors.HexColor('#f8fafd')
            table_styles.append(('BACKGROUND', (0, r_idx), (-1, r_idx), bg))
            
        # Precise Column Alignments (Numbers Right, IDs/Dates Center, Text Left)
        for c_idx, col in enumerate(columns):
            c_low = col.lower()
            if any(k in c_low for k in ['debit', 'credit', 'balance', 'amount', 'total', 'interest', 'rs', '₹', 'rate', 'price']):
                table_styles.append(('ALIGN', (c_idx, 0), (c_idx, -1), 'RIGHT'))
            elif any(k in c_low for k in ['date', 'voucher', 'tx id', 'id', 'vr no', 'status', 'code', 'account no']):
                table_styles.append(('ALIGN', (c_idx, 0), (c_idx, -1), 'CENTER'))
            else:
                table_styles.append(('ALIGN', (c_idx, 0), (c_idx, -1), 'LEFT'))
        
        t.setStyle(TableStyle(table_styles))
        elements.append(t)
        
        elements.append(Spacer(1, 10))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, alignment=1, textColor=colors.HexColor('#666666'))
        elements.append(Paragraph(f"Generated on: {datetime.now(IST).strftime('%d-%b-%Y %I:%M %p IST')}", footer_style))
        
    else:
        elements.append(Paragraph("No records found for this report.", styles['Normal']))
        
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

@cache_data
def create_csv_report(title, df, from_date=None, to_date=None):
    """
    Exports a professional CSV report matching the PDF header, title, date range,
    and structured columns with a totals summary row.
    """
    import csv
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    
    # 1. Company Header (matching PDF)
    writer.writerow(["AARSHA NIDHI LIMITED"])
    writer.writerow(["6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501"])
    writer.writerow(["CIN: U65990KL2021PLN069978 | Ph: 0471-2994535"])
    
    # 2. Report Title & Date Scope
    date_str = f"From: {format_date_str(from_date)} To: {format_date_str(to_date)}" if from_date and to_date else ""
    writer.writerow([f"{title.upper()} - {date_str}" if date_str else title.upper()])
    writer.writerow([f"Generated on: {datetime.now(IST).strftime('%d-%b-%Y %I:%M %p IST')}"])
    writer.writerow([])  # Blank line separator
    
    if not df.empty:
        # 3. Columns
        cols = list(df.columns)
        writer.writerow(cols)
        
        # 4. Rows with clean number formatting
        total_dr = 0.0
        total_cr = 0.0
        
        for row in df.values:
            cleaned_row = []
            for col_idx, val in enumerate(row):
                col_name = cols[col_idx].lower()
                if isinstance(val, (int, float)):
                    if any(k in col_name for k in ['debit', 'credit', 'balance', 'amount', 'total', 'interest', 'rs', '₹']):
                        if 'debit' in col_name:
                            total_dr += float(val)
                        elif 'credit' in col_name:
                            total_cr += float(val)
                        cleaned_row.append(f"{val:.2f}")
                    else:
                        cleaned_row.append(str(val))
                else:
                    cleaned_row.append("" if val is None else format_date_str(str(val)))
            writer.writerow(cleaned_row)
            
        # 5. Summary Footer Row
        summary_row = []
        for c_idx, col in enumerate(cols):
            c_name = col.lower()
            if c_idx == 0:
                summary_row.append("TOTALS")
            elif 'debit' in c_name:
                summary_row.append(f"{total_dr:.2f}")
            elif 'credit' in c_name:
                summary_row.append(f"{total_cr:.2f}")
            elif 'balance' in c_name and len(df) > 0:
                last_bal = df.iloc[-1][col]
                summary_row.append(f"{float(last_bal):.2f}" if isinstance(last_bal, (int, float)) else str(last_bal))
            elif c_idx == 2 or (c_idx == 3 and len(cols) > 4):
                summary_row.append(f"Total Dr: Rs.{total_dr:,.2f} | Total Cr: Rs.{total_cr:,.2f}")
            else:
                summary_row.append("")
        writer.writerow([])
        writer.writerow(summary_row)
    else:
        writer.writerow(["No records found for this report."])
        
    return buffer.getvalue().encode('utf-8-sig')

@cache_data
def create_excel_report(title, df, from_date=None, to_date=None):
    """
    Exports a fully-styled Excel (.xlsx) report matching the PDF design 100%:
    - Navy Blue header (#1F4E78) with white bold text
    - Company branding & CIN subheadings
    - Alternating row backgrounds (#FFFFFF and #F8FAFD)
    - Grid borders (#D0D5DD)
    - Currency formatting (#,##0.00) and column alignments
    - Bold summary footer with double underline
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        # Fallback to CSV bytes if openpyxl is still installing on cloud server
        return create_csv_report(title, df, from_date, to_date)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.views.sheetView[0].showGridLines = True

    cols = list(df.columns) if not df.empty else ["A", "B", "C", "D", "E"]
    num_cols = len(cols)
    last_col_letter = get_column_letter(num_cols)

    # Styles
    border_color = "D0D5DD"
    thin_border = Border(
        left=Side(style='thin', color=border_color),
        right=Side(style='thin', color=border_color),
        top=Side(style='thin', color=border_color),
        bottom=Side(style='thin', color=border_color)
    )

    # Row 1: Company Header
    ws.merge_cells(f"A1:{last_col_letter}1")
    c1 = ws["A1"]
    c1.value = "AARSHA NIDHI LIMITED"
    c1.font = Font(name="Segoe UI", size=14, bold=True, color="1F4E78")
    c1.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    # Row 2: Address
    ws.merge_cells(f"A2:{last_col_letter}2")
    c2 = ws["A2"]
    c2.value = "6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501"
    c2.font = Font(name="Segoe UI", size=9, color="4B5563")
    c2.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 16

    # Row 3: CIN
    ws.merge_cells(f"A3:{last_col_letter}3")
    c3 = ws["A3"]
    c3.value = "CIN: U65990KL2021PLN069978 | Ph: 0471-2994535"
    c3.font = Font(name="Segoe UI", size=9, color="4B5563")
    c3.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 16

    # Row 4: Title & Date Range
    ws.merge_cells(f"A4:{last_col_letter}4")
    c4 = ws["A4"]
    date_str = f" (From: {format_date_str(from_date)} To: {format_date_str(to_date)})" if from_date and to_date else ""
    c4.value = f"{title.upper()}{date_str}"
    c4.font = Font(name="Segoe UI", size=11, bold=True, color="1F4E78")
    c4.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[4].height = 22

    # Row 5: Blank separator
    ws.row_dimensions[5].height = 8

    # Row 6: Table Headers
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Segoe UI", size=9.5, bold=True, color="FFFFFF")
    ws.row_dimensions[6].height = 24

    for c_idx, col in enumerate(cols, 1):
        cell = ws.cell(row=6, column=c_idx, value=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = thin_border
        c_low = col.lower()
        if any(k in c_low for k in ['debit', 'credit', 'balance', 'amount']):
            cell.alignment = Alignment(horizontal="right", vertical="center")
        elif any(k in c_low for k in ['date', 'voucher', 'id', 'vr no', 'code']):
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # Data Rows
    alt_fill = PatternFill(start_color="F8FAFD", end_color="F8FAFD", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    total_dr = 0.0
    total_cr = 0.0
    current_row = 7

    if not df.empty:
        for r_idx, row in enumerate(df.values):
            ws.row_dimensions[current_row].height = 19
            fill = white_fill if r_idx % 2 == 0 else alt_fill
            
            for c_idx, val in enumerate(row, 1):
                cell = ws.cell(row=current_row, column=c_idx)
                cell.fill = fill
                cell.border = thin_border
                cell.font = Font(name="Segoe UI", size=9)
                
                c_name = cols[c_idx - 1].lower()
                if isinstance(val, (int, float)):
                    cell.value = float(val)
                    if any(k in c_name for k in ['debit', 'credit', 'balance', 'amount', 'total']):
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                        if 'debit' in c_name: total_dr += float(val)
                        elif 'credit' in c_name: total_cr += float(val)
                else:
                    cell.value = format_date_str(str(val)) if val is not None else ""
                    if any(k in c_name for k in ['date', 'voucher', 'id', 'vr no']):
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            current_row += 1

        # Summary / Totals Row
        ws.row_dimensions[current_row].height = 24
        tot_border = Border(
            top=Side(style='thin', color="1F4E78"),
            bottom=Side(style='double', color="1F4E78"),
            left=Side(style='thin', color=border_color),
            right=Side(style='thin', color=border_color)
        )
        tot_font = Font(name="Segoe UI", size=9.5, bold=True, color="1F4E78")
        tot_fill = PatternFill(start_color="EAEEF4", end_color="EAEEF4", fill_type="solid")

        for c_idx, col in enumerate(cols, 1):
            cell = ws.cell(row=current_row, column=c_idx)
            cell.border = tot_border
            cell.font = tot_font
            cell.fill = tot_fill
            c_name = col.lower()
            if c_idx == 1:
                cell.value = "TOTALS"
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif 'debit' in c_name:
                cell.value = total_dr
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif 'credit' in c_name:
                cell.value = total_cr
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif 'balance' in c_name and len(df) > 0:
                last_b = df.iloc[-1][cols[c_idx - 1]]
                cell.value = float(last_b) if isinstance(last_b, (int, float)) else last_b
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif c_idx == 3:
                cell.value = f"Total Dr: Rs.{total_dr:,.2f} | Total Cr: Rs.{total_cr:,.2f}"
                cell.alignment = Alignment(horizontal="left", vertical="center")

        # Auto-adjust column widths
        for col_cells in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col_cells[0].column)
            for cell in col_cells[5:]:
                if cell.value:
                    val_str = str(cell.value)
                    max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(min(max_len + 4, 38), 12)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def generate_voucher_pdf(voucher_type, voucher_data, jv_id=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A5, 
                           rightMargin=10*mm, leftMargin=10*mm, 
                           topMargin=12*mm, bottomMargin=12*mm)
    elements = []
    
    available_width = A5[0] - (20*mm)
    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle(
        'VoucherHeader',
        parent=styles['Heading1'],
        fontSize=11,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    )
    
    sub_header_style = ParagraphStyle(
        'VoucherSubHeader',
        parent=styles['Normal'],
        fontSize=7,
        alignment=1,
        spaceAfter=2,
        textColor=colors.HexColor('#555555')
    )
    
    title_style = ParagraphStyle(
        'VoucherTitle',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'VoucherNormal',
        parent=styles['Normal'],
        fontSize=8,
        leading=11
    )
    
    bold_style = ParagraphStyle(
        'VoucherBold',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Paragraph("6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", sub_header_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Ph: 0471-2994535", sub_header_style))
    elements.append(Spacer(1, 4))
    
    if voucher_type == 'CB':
        date_val, v_num, part, dr, cr, acc_code, narr = voucher_data[0]
        acc_name = get_account_name(acc_code)
        account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
        
        elements.append(Paragraph("CASH VOUCHER (CB)", title_style))
        elements.append(Spacer(1, 4))
        
        voucher_content = [
            ["Voucher No:", v_num, "Date:", format_date_str(date_val)],
            ["Particulars:", part, "", ""],
            ["Account Head:", account_display, "", ""],
            ["Amount:", f"Debit (Receipt): Rs.{dr:,.2f}" if dr > 0 else f"Credit (Payment): Rs.{cr:,.2f}", "", ""],
            ["Narration:", narr if narr else 'N/A', "", ""],
        ]
        
        table_data = []
        for row in voucher_content:
            para_row = []
            for i, cell in enumerate(row):
                if i == 0:
                    para_row.append(Paragraph(f"<b>{cell}</b>", bold_style))
                else:
                    para_row.append(Paragraph(str(cell), normal_style))
            table_data.append(para_row)
        
        col_widths = [available_width * 0.22, available_width * 0.38, available_width * 0.15, available_width * 0.25]
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('SPAN', (1, 1), (-1, 1)),
            ('SPAN', (1, 2), (-1, 2)),
            ('SPAN', (1, 3), (-1, 3)),
            ('SPAN', (1, 4), (-1, 4)),
        ]))
        elements.append(t)
        
    elif voucher_type == 'BB':
        date_val, v_num, bank_n, part, dr, cr, acc_code, narr = voucher_data[0]
        acc_name = get_account_name(acc_code)
        account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
        
        elements.append(Paragraph("BANK VOUCHER (BB)", title_style))
        elements.append(Spacer(1, 4))
        
        voucher_content = [
            ["Voucher No:", v_num, "Date:", format_date_str(date_val)],
            ["Bank:", bank_n, "", ""],
            ["Particulars:", part, "", ""],
            ["Account Head:", account_display, "", ""],
            ["Amount:", f"Debit (Deposit): Rs.{dr:,.2f}" if dr > 0 else f"Credit (Withdrawal): Rs.{cr:,.2f}", "", ""],
            ["Narration:", narr if narr else 'N/A', "", ""],
        ]
        
        table_data = []
        for row in voucher_content:
            para_row = []
            for i, cell in enumerate(row):
                if i == 0:
                    para_row.append(Paragraph(f"<b>{cell}</b>", bold_style))
                else:
                    para_row.append(Paragraph(str(cell), normal_style))
            table_data.append(para_row)
        
        col_widths = [available_width * 0.20, available_width * 0.40, available_width * 0.15, available_width * 0.25]
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('SPAN', (1, 1), (-1, 1)),
            ('SPAN', (1, 2), (-1, 2)),
            ('SPAN', (1, 3), (-1, 3)),
            ('SPAN', (1, 4), (-1, 4)),
            ('SPAN', (1, 5), (-1, 5)),
        ]))
        elements.append(t)
        
    elif voucher_type == 'JV':
        elements.append(Paragraph("JOURNAL VOUCHER (JV)", title_style))
        elements.append(Spacer(1, 4))
        
        jv_date = voucher_data[0][0]
        narration_text = voucher_data[0][1]
        
        header_data = [
            [Paragraph(f"<b>JV ID:</b> JV-{jv_id if jv_id else 'N/A'}", bold_style),
             Paragraph(f"<b>Date:</b> {format_date_str(jv_date)}", normal_style)]
        ]
        header_t = Table(header_data, colWidths=[available_width*0.5, available_width*0.5])
        header_t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(header_t)
        elements.append(Spacer(1, 6))
        
        col1_width = available_width * 0.55
        col2_width = available_width * 0.225
        col3_width = available_width * 0.225
        
        table_data = [[Paragraph("<b>Account Head</b>", bold_style), 
                      Paragraph("<b>Debit (Rs.)</b>", bold_style), 
                      Paragraph("<b>Credit (Rs.)</b>", bold_style)]]
        
        total_dr = 0
        total_cr = 0
        for row in voucher_data:
            _, _, acc_code, acc_name, dr, cr = row
            account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
            table_data.append([
                Paragraph(account_display, normal_style),
                Paragraph(f"{dr:,.2f}" if dr > 0 else "-", normal_style),
                Paragraph(f"{cr:,.2f}" if cr > 0 else "-", normal_style)
            ])
            total_dr += dr
            total_cr += cr
        
        table_data.append([
            Paragraph("<b>Total</b>", bold_style),
            Paragraph(f"<b>{total_dr:,.2f}</b>", bold_style),
            Paragraph(f"<b>{total_cr:,.2f}</b>", bold_style)
        ])
        
        t = Table(table_data, colWidths=[col1_width, col2_width, col3_width])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Narration:</b> {narration_text if narration_text else 'N/A'}", normal_style))
    
    elements.append(Spacer(1, 15))
    sign_line = "_" * 60
    elements.append(Paragraph(sign_line, ParagraphStyle('Line', alignment=1, fontSize=7)))
    elements.append(Paragraph("Authorized Signature / Stamp", ParagraphStyle('Sign', alignment=1, fontSize=7, textColor=colors.HexColor('#555555'))))
    elements.append(Spacer(1, 3))
    timestamp_style = ParagraphStyle('Timestamp', alignment=1, fontSize=6, textColor=colors.HexColor('#999999'))
    elements.append(Paragraph(f"Printed: {datetime.now(IST).strftime('%d-%b-%Y %I:%M %p IST')}", timestamp_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def generate_fd_pdf(fd_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=15*mm, leftMargin=15*mm, 
                           topMargin=15*mm, bottomMargin=15*mm)
    elements = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle', 
        parent=styles['Heading1'], 
        fontSize=16, 
        textColor=colors.HexColor('#b94a00'), 
        alignment=1,  
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=1,  
        spaceAfter=2,
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle', 
        parent=styles['Heading2'], 
        fontSize=13, 
        alignment=1,  
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    
    status_style = ParagraphStyle(
        'StatusStyle', 
        parent=styles['Normal'], 
        fontSize=12, 
        fontName='Helvetica-Bold',
        alignment=1,  
        spaceAfter=6
    )
    
    detail_label = ParagraphStyle(
        'DetailLabel', 
        parent=styles['Normal'], 
        fontSize=10, 
        fontName='Helvetica-Bold',
        alignment=0
    )
    
    detail_value = ParagraphStyle(
        'DetailValue', 
        parent=styles['Normal'], 
        fontSize=10, 
        alignment=0
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader', 
        parent=styles['Normal'], 
        fontSize=9, 
        fontName='Helvetica-Bold', 
        textColor=colors.black, 
        alignment=1,  
        backColor=colors.HexColor('#f2f2f2')
    )
    
    table_cell_center = ParagraphStyle(
        'TableCellCenter', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=1  
    )
    
    table_cell_left = ParagraphStyle(
        'TableCellLeft', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=0  
    )
    
    table_cell_right = ParagraphStyle(
        'TableCellRight', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=2  
    )
    
    fd_id, c_name, street, city, state, pincode, principal, tenure, rate, maturity, nominee, created_at, status, closed_date = fd_data[:14]
    op_bal_date = fd_data[14] if len(fd_data) > 14 else created_at
    full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
    status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"
    
    elements.append(Paragraph("AARSHA NIDHI LIMITED", title_style))
    elements.append(Paragraph("6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", subtitle_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Ph: 0471-2994535", subtitle_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("FIXED DEPOSIT RECEIPT / LEDGER", heading_style))
    
    status_color = colors.red if status == 'CLOSED' else colors.green
    elements.append(Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", status_style))
    
    detail_data = [
        [Paragraph("<b>FDR No. / A/c No:</b>", detail_label), Paragraph(f"FD-{fd_id:05d}", detail_value),
         Paragraph("<b>A/c Opening Date:</b>", detail_label), Paragraph(format_date_str(created_at), detail_value)],
        [Paragraph("<b>Name:</b>", detail_label), Paragraph(str(c_name), detail_value),
         Paragraph("<b>Opening Balance Date:</b>", detail_label), Paragraph(format_date_str(op_bal_date), detail_value)],
        [Paragraph("<b>Address:</b>", detail_label), Paragraph(str(full_address), detail_value),
         Paragraph("<b>Principal Amount:</b>", detail_label), Paragraph(f"₹{principal:,.2f}", detail_value)],
        [Paragraph("<b>Period / Tenure:</b>", detail_label), Paragraph(f"{tenure} MONTHS", detail_value),
         Paragraph("<b>Interest Rate:</b>", detail_label), Paragraph(f"{rate}% p.a.", detail_value)],
        [Paragraph("<b>Nominee:</b>", detail_label), Paragraph(nominee if nominee else 'N/A', detail_value),
         Paragraph("<b>Maturity Amount:</b>", detail_label), Paragraph(f"₹{maturity:,.2f}", detail_value)],
        [Paragraph("<b>Status:</b>", detail_label), Paragraph(status_text, detail_value),
         Paragraph("<b>Closed Date:</b>" if status == 'CLOSED' else "", detail_label), Paragraph(format_date_str(closed_date) if status == 'CLOSED' else "", detail_value)],
    ]
    
    detail_table = Table(detail_data, colWidths=[35*mm, 50*mm, 35*mm, 50*mm])
    detail_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 6))
    
    box_style = ParagraphStyle(
        'BoxStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=0,
        borderPadding=6,
    )
    elements.append(Paragraph(f"<b>Deposit Repayable:</b> Principal sum of <b>₹{principal:,.2f}</b> repayable after {tenure} months with interest at {rate}% p.a.", box_style))
    elements.append(Spacer(1, 8))
    
    ledger_data = [
        [Paragraph("<b>Date</b>", table_header_style),
         Paragraph("<b>Particulars</b>", table_header_style),
         Paragraph("<b>Payment / Debit</b>", table_header_style),
         Paragraph("<b>Receipt / Credit</b>", table_header_style),
         Paragraph("<b>Balance</b>", table_header_style),
         Paragraph("<b>Int Paid</b>", table_header_style),
         Paragraph("<b>TDS</b>", table_header_style)]
    ]
    
    ledger_data.append([
        Paragraph(format_date_str(op_bal_date), table_cell_center),
        Paragraph("Opening Balance / Principal Deposit", table_cell_left),
        Paragraph("-", table_cell_center),
        Paragraph(f"₹{principal:,.2f}", table_cell_right),
        Paragraph(f"₹{principal:,.2f}", table_cell_right),
        Paragraph("0", table_cell_center),
        Paragraph("0", table_cell_center)
    ])
    
    if status == 'CLOSED':
        ledger_data.append([
            Paragraph(format_date_str(closed_date), table_cell_center),
            Paragraph("FD Closed / Maturity Payment", table_cell_left),
            Paragraph(f"₹{maturity:,.2f}", table_cell_right),
            Paragraph("-", table_cell_center),
            Paragraph("₹0.00", table_cell_right),
            Paragraph(f"₹{maturity - principal:,.2f}", table_cell_right),
            Paragraph("0", table_cell_center)
        ])
    
    ledger_table = Table(ledger_data, colWidths=[28*mm, 38*mm, 26*mm, 26*mm, 26*mm, 22*mm, 20*mm])
    ledger_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(ledger_table)
    elements.append(Spacer(1, 16))
    
    sig_data = [
        ["Manager", "Accountant", "Chairman / MD"]
    ]
    sig_table = Table(sig_data, colWidths=[50*mm, 50*mm, 50*mm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(sig_table)
    
    if status == 'CLOSED':
        elements.append(Spacer(1, 6))
        warning_style = ParagraphStyle(
            'WarningStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.red,
            alignment=1,
            fontName='Helvetica-Bold',
            spaceAfter=4
        )
        elements.append(Paragraph(f"⚠️ This Fixed Deposit has been CLOSED on {format_date_str(closed_date)}" if closed_date else "⚠️ This Fixed Deposit has been CLOSED", warning_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def generate_rd_pdf(rd_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=15*mm, leftMargin=15*mm,
                           topMargin=15*mm, bottomMargin=15*mm)
    elements = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle', 
        parent=styles['Heading1'], 
        fontSize=16, 
        textColor=colors.HexColor('#1b4f72'), 
        alignment=1,  
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=1,  
        spaceAfter=2,
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle', 
        parent=styles['Heading2'], 
        fontSize=13, 
        alignment=1,  
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    
    status_style = ParagraphStyle(
        'StatusStyle', 
        parent=styles['Normal'], 
        fontSize=12, 
        fontName='Helvetica-Bold',
        alignment=1,  
        spaceAfter=6
    )
    
    detail_label = ParagraphStyle(
        'DetailLabel', 
        parent=styles['Normal'], 
        fontSize=10, 
        fontName='Helvetica-Bold',
        alignment=0
    )
    
    detail_value = ParagraphStyle(
        'DetailValue', 
        parent=styles['Normal'], 
        fontSize=10, 
        alignment=0
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader', 
        parent=styles['Normal'], 
        fontSize=9, 
        fontName='Helvetica-Bold', 
        textColor=colors.black, 
        alignment=1,  
        backColor=colors.HexColor('#ebf5fb')
    )
    
    table_cell_center = ParagraphStyle(
        'TableCellCenter', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=1  
    )
    
    table_cell_left = ParagraphStyle(
        'TableCellLeft', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=0  
    )
    
    table_cell_right = ParagraphStyle(
        'TableCellRight', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=2  
    )
    
    if len(rd_data) > 19:
        rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date, rd_acc_no, col_balance, scheme_name, maturity_date = rd_data[:19]
        op_bal_date = rd_data[19]
    elif len(rd_data) == 19:
        rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date, rd_acc_no, col_balance, scheme_name, maturity_date = rd_data[:19]
        op_bal_date = created_at
    elif len(rd_data) == 18:
        rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date, rd_acc_no, col_balance, scheme_name = rd_data[:18]
        maturity_date = "2026-12-20"
        op_bal_date = created_at
    elif len(rd_data) == 17:
        rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date, rd_acc_no, col_balance = rd_data[:17]
        scheme_name = "SWAYAMVARA KSHEMANIDHI"
        maturity_date = "2026-12-20"
        op_bal_date = created_at
    elif len(rd_data) == 16:
        rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date, rd_acc_no = rd_data[:16]
        col_balance = monthly_amt * paid_inst
        scheme_name = "SWAYAMVARA KSHEMANIDHI"
        maturity_date = "2026-12-20"
        op_bal_date = created_at
    else:
        rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date = rd_data[:15]
        rd_acc_no = f"RD-{rd_id:05d}"
        col_balance = monthly_amt * paid_inst
        scheme_name = "SWAYAMVARA KSHEMANIDHI"
        maturity_date = "2026-12-20"
        op_bal_date = created_at

    full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
    total_deposited = col_balance
    status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"

    if status == 'CLOSED' or int(paid_inst or 0) < int(tenure or 1):
        try:
            m_amt = float(monthly_amt or 0.0)
            r_val = float(rate or 0.0)
            p_inst = int(paid_inst or 0)
            if p_inst > 0:
                if r_val > 0:
                    i = r_val / 400.0
                    accrued_mat = sum(m_amt * ((1.0 + i) ** ((p_inst - k + 1) / 3.0)) for k in range(1, p_inst + 1))
                    maturity = round(accrued_mat, 2)
                else:
                    maturity = round(m_amt * p_inst, 2)
        except Exception:
            pass
    
    elements.append(Paragraph("AARSHA NIDHI LIMITED", title_style))
    elements.append(Paragraph("6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", subtitle_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Ph: 0471-2994535", subtitle_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("RECURRING DEPOSIT RECEIPT / LEDGER", heading_style))
    
    status_color = colors.red if status == 'CLOSED' else colors.blue
    elements.append(Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", status_style))
    
    years = int(tenure) // 12
    months = int(tenure) % 12
    if years > 0 and months > 0:
        tenure_display = f"{tenure} MONTHS ({years}Y {months}M)"
    elif years > 0:
        tenure_display = f"{tenure} MONTHS ({years} Years)"
    else:
        tenure_display = f"{tenure} MONTHS"

    detail_data = [
        [Paragraph("<b>RDR No. / A/c No:</b>", detail_label), Paragraph(str(rd_acc_no), detail_value),
         Paragraph("<b>Scheme:</b>", detail_label), Paragraph(str(scheme_name), detail_value)],
        [Paragraph("<b>A/c Opening Date:</b>", detail_label), Paragraph(format_date_str(created_at), detail_value),
         Paragraph("<b>Maturity Date:</b>", detail_label), Paragraph(format_date_str(maturity_date), detail_value)],
        [Paragraph("<b>Name:</b>", detail_label), Paragraph(str(c_name), detail_value),
         Paragraph("<b>Opening Balance Date:</b>", detail_label), Paragraph(format_date_str(op_bal_date), detail_value)],
        [Paragraph("<b>Address:</b>", detail_label), Paragraph(str(full_address), detail_value),
         Paragraph("<b>Interest Rate:</b>", detail_label), Paragraph(f"{rate}% p.a.", detail_value)],
        [Paragraph("<b>Monthly Installment:</b>", detail_label), Paragraph(f"₹{monthly_amt:,.2f}", detail_value),
         Paragraph("<b>Nominee:</b>", detail_label), Paragraph(nominee if nominee else 'N/A', detail_value)],
        [Paragraph("<b>Tenure:</b>", detail_label), Paragraph(tenure_display, detail_value),
         Paragraph("<b>Installments Paid:</b>", detail_label), Paragraph(f"{paid_inst} / {tenure}", detail_value)],
        [Paragraph("<b>Total Deposited:</b>", detail_label), Paragraph(f"₹{total_deposited:,.2f}", detail_value),
         Paragraph("<b>Maturity Amount:</b>", detail_label), Paragraph(f"₹{maturity:,.2f}", detail_value)],
        [Paragraph("<b>Status:</b>", detail_label), Paragraph(status_text, detail_value),
         Paragraph("<b>Closed Date:</b>" if status == 'CLOSED' else "", detail_label), Paragraph(format_date_str(closed_date) if status == 'CLOSED' else "", detail_value)],
    ]
    
    detail_table = Table(detail_data, colWidths=[40*mm, 45*mm, 40*mm, 45*mm])
    detail_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 6))
    
    box_style = ParagraphStyle(
        'BoxStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=0,
        borderPadding=6,
    )
    elements.append(Paragraph(f"<b>Deposit Repayable:</b> Recurring Deposit of <b>₹{monthly_amt:,.2f}</b> monthly for {tenure} months. Total balance accumulated: <b>₹{total_deposited:,.2f}</b>.", box_style))
    elements.append(Spacer(1, 8))
    
    ledger_data = [
        [Paragraph("<b>Date</b>", table_header_style),
         Paragraph("<b>Particulars</b>", table_header_style),
         Paragraph("<b>Payment / Debit</b>", table_header_style),
         Paragraph("<b>Receipt / Credit</b>", table_header_style),
         Paragraph("<b>Balance</b>", table_header_style),
         Paragraph("<b>Inst. Paid</b>", table_header_style)]
    ]
    
    ledger_data.append([
        Paragraph(format_date_str(op_bal_date), table_cell_center),
        Paragraph("RD Account Opening & Installments", table_cell_left),
        Paragraph("-", table_cell_center),
        Paragraph(f"₹{total_deposited:,.2f}", table_cell_right),
        Paragraph(f"₹{total_deposited:,.2f}", table_cell_right),
        Paragraph(str(paid_inst), table_cell_center)
    ])
    
    if status == 'CLOSED':
        ledger_data.append([
            Paragraph(format_date_str(closed_date), table_cell_center),
            Paragraph("RD Closed / Maturity Payment", table_cell_left),
            Paragraph(f"₹{maturity:,.2f}", table_cell_right),
            Paragraph("-", table_cell_center),
            Paragraph("₹0.00", table_cell_right),
            Paragraph(str(paid_inst), table_cell_center)
        ])
    
    ledger_table = Table(ledger_data, colWidths=[30*mm, 40*mm, 28*mm, 28*mm, 28*mm, 26*mm])
    ledger_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ebf5fb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(ledger_table)
    elements.append(Spacer(1, 16))
    
    sig_data = [
        ["Manager", "Accountant", "Chairman / MD"]
    ]
    sig_table = Table(sig_data, colWidths=[50*mm, 50*mm, 50*mm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(sig_table)
    
    if status == 'CLOSED':
        elements.append(Spacer(1, 6))
        warning_style = ParagraphStyle(
            'WarningStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.red,
            alignment=1,
            fontName='Helvetica-Bold',
            spaceAfter=4
        )
        elements.append(Paragraph(f"⚠️ This Recurring Deposit has been CLOSED on {format_date_str(closed_date)}" if closed_date else "⚠️ This Recurring Deposit has been CLOSED", warning_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def extract_or_build_ledger_rows(loan_data, repayments_df=None):
    """
    Constructs normalized ledger rows:
    [(date, voucher_no, particulars, mode, debit, credit, balance)]
    Starts with Disbursal Debit, followed by Repayment Credits, computing running balance.
    """
    tot_rep = float(loan_data.get("total_amount", loan_data.get("total_repayable", 0.0)) or 0.0)
    princ = float(loan_data.get("loan_amount", loan_data.get("principal_amount", 0.0)) or 0.0)
    tot_int = float(loan_data.get("total_interest", 0.0) or 0.0)
    if tot_rep == 0.0 and princ > 0.0:
        tot_rep = princ + tot_int

    s_date = str(loan_data.get("loan_date", loan_data.get("sanction_date", loan_data.get("loan_from", ""))))
    l_no = str(loan_data.get("loan_no", ""))
    
    rows = []
    
    if repayments_df is not None and hasattr(repayments_df, "empty") and not repayments_df.empty:
        cols = [str(c).upper() for c in repayments_df.columns]
        has_debit = any("DEBIT" in c for c in cols)
        
        if has_debit:
            for _, r in repayments_df.iterrows():
                d_val = str(r.get("Date", r.get("DATE", "")))
                v_val = str(r.get("Voucher No", r.get("VOUCHER NO", "")))
                p_val = str(r.get("Particulars", r.get("PARTICULARS", r.get("Narration", r.get("NARRATION", "")))))
                m_val = str(r.get("Payment Mode", r.get("PAYMENT MODE", r.get("Mode", ""))))
                
                dr_raw = r.get("Debit (Rs.)", r.get("Debit (₹)", r.get("DEBIT (Rs.)", r.get("Debit", r.get("DEBIT", 0.0)))))
                cr_raw = r.get("Credit (Rs.)", r.get("Credit (₹)", r.get("CREDIT (Rs.)", r.get("Credit", r.get("CREDIT", 0.0)))))
                bal_raw = r.get("Balance (Rs.)", r.get("Balance (₹)", r.get("BALANCE (Rs.)", r.get("Balance", r.get("BALANCE", 0.0)))))
                
                try:
                    dr_val = float(dr_raw or 0.0)
                except (ValueError, TypeError):
                    dr_val = 0.0
                try:
                    cr_val = float(cr_raw or 0.0)
                except (ValueError, TypeError):
                    cr_val = 0.0
                try:
                    bal_val = float(bal_raw or 0.0)
                except (ValueError, TypeError):
                    bal_val = 0.0
                    
                rows.append((d_val, v_val, p_val, m_val, dr_val, cr_val, bal_val))
            return rows
        else:
            running_bal = tot_rep
            rows.append((
                s_date,
                l_no,
                f"Loan Disbursed (Principal ₹{princ:,.2f} + Int ₹{tot_int:,.2f})",
                "Disbursal",
                tot_rep,
                0.0,
                running_bal
            ))
            for _, r in repayments_df.iterrows():
                d_val = str(r.get("Date", r.get("payment_date", "")))
                v_val = str(r.get("Voucher No", r.get("voucher_no", "")))
                amt_raw = r.get("Amount Paid (₹)", r.get("Amount Paid", r.get("amount_paid", 0.0)))
                try:
                    amt_val = float(amt_raw or 0.0)
                except (ValueError, TypeError):
                    amt_val = 0.0
                m_val = str(r.get("Payment Mode", r.get("payment_mode", "Cash")))
                p_val = str(r.get("Narration", r.get("narration", "Loan Repayment Received")))
                running_bal = round(running_bal - amt_val, 2)
                rows.append((d_val, v_val, p_val, m_val, 0.0, amt_val, running_bal))
            return rows
    else:
        rows.append((
            s_date,
            l_no,
            f"Loan Disbursed (Principal ₹{princ:,.2f} + Int ₹{tot_int:,.2f})",
            "Disbursal",
            tot_rep,
            0.0,
            tot_rep
        ))
        return rows


@cache_data
def create_loan_passbook_excel(loan_data, schedule_df, repayments_df=None):
    """
    Exports a styled Excel (.xlsx) Loan Passbook & Statement:
    - Company & Passbook Header
    - Customer & Guarantor Details Block
    - Financial Terms & EMI Summary Block
    - Section 1: Customer Repayment Ledger (Debit / Credit Transactions) - FIRST
    - Section 2: 12-Month EMI Amortization Schedule Table - SECOND
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return b""

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Loan Passbook"
    ws.views.sheetView[0].showGridLines = True

    # Styles
    navy_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    light_blue_fill = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
    soft_gray_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    header_section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    font_title = Font(name="Segoe UI", size=14, bold=True, color="1F4E78")
    font_sub = Font(name="Segoe UI", size=9, color="4B5563")
    font_section = Font(name="Segoe UI", size=11, bold=True, color="1F4E78")
    font_header_white = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Segoe UI", size=10, bold=True, color="111827")
    font_normal = Font(name="Segoe UI", size=9.5, color="111827")

    border_color = "D0D5DD"
    thin_side = Side(style='thin', color=border_color)
    double_bottom_side = Side(style='double', color="1F4E78")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    summary_border = Border(top=thin_side, bottom=double_bottom_side, left=thin_side, right=thin_side)

    # 1. Company Header
    ws.merge_cells("A1:G1")
    ws["A1"] = "AARSHA NIDHI LIMITED"
    ws["A1"].font = font_title
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    ws.merge_cells("A2:G2")
    ws["A2"] = "6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501"
    ws["A2"].font = font_sub
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 14

    ws.merge_cells("A3:G3")
    ws["A3"] = "CIN: U65990KL2021PLN069978 | Ph: 0471-2994535"
    ws["A3"].font = font_sub
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 14

    ws.merge_cells("A4:G4")
    ws["A4"] = "LOAN PASSBOOK / LOAN STATEMENT OF ACCOUNT"
    ws["A4"].font = Font(name="Segoe UI", size=12, bold=True, color="FFFFFF")
    ws["A4"].fill = navy_fill
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[4].height = 22

    # 2. Loan & Borrower Info Block
    info_rows = [
        ("LOAN ACCOUNT NO", str(loan_data.get("loan_no", "")), "STATUS", str(loan_data.get("status", "ACTIVE"))),
        ("LOAN PARTY NAME", str(loan_data.get("party_name", "")), "MEMBER ACC NO", str(loan_data.get("account_no", "N/A"))),
        ("ADDRESS", str(loan_data.get("address", "")), "MOBILE NUMBER", str(loan_data.get("mobile", ""))),
        ("GUARANTOR NAME", str(loan_data.get("guarantor_name", "")), "RELATION", str(loan_data.get("guarantor_relation", "Guarantor"))),
        ("GUARANTOR ADDRESS", str(loan_data.get("guarantor_address", "")), "GUARANTOR MOBILE", str(loan_data.get("guarantor_phone", ""))),
    ]

    r_idx = 6
    for lbl1, val1, lbl2, val2 in info_rows:
        ws.cell(row=r_idx, column=1, value=lbl1).font = font_bold
        ws.cell(row=r_idx, column=1).fill = soft_gray_fill
        ws.cell(row=r_idx, column=2, value=val1).font = font_normal
        ws.merge_cells(start_row=r_idx, start_column=2, end_row=r_idx, end_column=4)

        ws.cell(row=r_idx, column=5, value=lbl2).font = font_bold
        ws.cell(row=r_idx, column=5).fill = soft_gray_fill
        ws.cell(row=r_idx, column=6, value=val2).font = font_normal
        ws.merge_cells(start_row=r_idx, start_column=6, end_row=r_idx, end_column=7)
        ws.row_dimensions[r_idx].height = 19
        r_idx += 1

    # 3. Financial Breakdown Block
    r_idx += 1
    ws.merge_cells(f"A{r_idx}:G{r_idx}")
    ws[f"A{r_idx}"] = "LOAN FINANCIAL TERMS & EMI SUMMARY"
    ws[f"A{r_idx}"].font = font_section
    ws[f"A{r_idx}"].fill = header_section_fill
    ws[f"A{r_idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r_idx].height = 20
    r_idx += 1

    fin_rows = [
        ("LOAN AMOUNT", float(loan_data.get("loan_amount", 0)), "PRINCIPAL EMI", float(loan_data.get("principal_emi", 0))),
        (f"INTEREST ({loan_data.get('interest_rate', 12)}%)", float(loan_data.get("total_interest", 0)), "INTEREST EMI", float(loan_data.get("interest_emi", 0))),
        ("TOTAL AMOUNT", float(loan_data.get("total_amount", 0)), "TOTAL MONTHLY EMI", float(loan_data.get("total_emi", 0))),
        ("LOAN DATE", str(loan_data.get("loan_date", "")), "DURATION", str(loan_data.get("duration", "12 Months"))),
        ("LOAN FROM", str(loan_data.get("loan_from", "")), "LOAN TO", str(loan_data.get("loan_to", ""))),
        ("FIRST EMI DUE", str(loan_data.get("first_emi_due", "")), "LAST EMI DUE", str(loan_data.get("last_emi_due", ""))),
    ]

    for lbl1, val1, lbl2, val2 in fin_rows:
        ws.cell(row=r_idx, column=1, value=lbl1).font = font_bold
        ws.cell(row=r_idx, column=1).fill = soft_gray_fill
        
        c_val1 = ws.cell(row=r_idx, column=2, value=val1)
        c_val1.font = font_bold if isinstance(val1, (int, float)) else font_normal
        if isinstance(val1, (int, float)):
            c_val1.number_format = '"Rs." #,##0.00'
        ws.merge_cells(start_row=r_idx, start_column=2, end_row=r_idx, end_column=4)

        ws.cell(row=r_idx, column=5, value=lbl2).font = font_bold
        ws.cell(row=r_idx, column=5).fill = soft_gray_fill
        
        c_val2 = ws.cell(row=r_idx, column=6, value=val2)
        c_val2.font = font_bold if isinstance(val2, (int, float)) else font_normal
        if isinstance(val2, (int, float)):
            c_val2.number_format = '"Rs." #,##0.00'
        ws.merge_cells(start_row=r_idx, start_column=6, end_row=r_idx, end_column=7)
        
        ws.row_dimensions[r_idx].height = 19
        r_idx += 1

    # 4. Section 1: Customer Repayment Ledger (Debit / Credit) - FIRST
    ledger_rows = extract_or_build_ledger_rows(loan_data, repayments_df)
    r_idx += 1
    ws.merge_cells(f"A{r_idx}:G{r_idx}")
    ws[f"A{r_idx}"] = "1. REPAYMENT TRANSACTIONS & CUSTOMER LEDGER (DEBIT / CREDIT)"
    ws[f"A{r_idx}"].font = font_section
    ws[f"A{r_idx}"].fill = header_section_fill
    ws[f"A{r_idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r_idx].height = 20
    r_idx += 1

    rep_headers = ["DATE", "VOUCHER NO", "PARTICULARS", "PAYMENT MODE", "DEBIT (Rs.)", "CREDIT (Rs.)", "BALANCE (Rs.)"]
    for c_idx, h in enumerate(rep_headers, 1):
        cell = ws.cell(row=r_idx, column=c_idx, value=h)
        cell.font = font_header_white
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[r_idx].height = 22
    r_idx += 1

    tot_dr = 0.0
    tot_cr = 0.0
    closing_bal = 0.0

    for d_val, v_val, p_val, m_val, dr_val, cr_val, bal_val in ledger_rows:
        tot_dr += dr_val
        tot_cr += cr_val
        closing_bal = bal_val

        r_vals = [d_val, v_val, p_val, m_val, dr_val, cr_val, bal_val]
        for col_idx, val in enumerate(r_vals, 1):
            c = ws.cell(row=r_idx, column=col_idx, value=val)
            c.font = font_normal
            c.border = thin_border
            if col_idx in [1, 2, 4]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 3:
                c.alignment = Alignment(horizontal="left", vertical="center")
            else:
                c.alignment = Alignment(horizontal="right", vertical="center")
                c.number_format = '#,##0.00'
        ws.row_dimensions[r_idx].height = 18
        r_idx += 1

    # Summary row for Repayments
    ws.cell(row=r_idx, column=1, value="TOTAL TRANSACTIONS & CLOSING DUE").font = font_bold
    ws.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=4)
    ws.cell(row=r_idx, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r_idx, column=1).fill = light_blue_fill

    c_dr = ws.cell(row=r_idx, column=5, value=tot_dr)
    c_dr.font = font_bold
    c_dr.fill = light_blue_fill
    c_dr.number_format = '#,##0.00'
    c_dr.alignment = Alignment(horizontal="right", vertical="center")

    c_cr = ws.cell(row=r_idx, column=6, value=tot_cr)
    c_cr.font = font_bold
    c_cr.fill = light_blue_fill
    c_cr.number_format = '#,##0.00'
    c_cr.alignment = Alignment(horizontal="right", vertical="center")

    c_bal = ws.cell(row=r_idx, column=7, value=closing_bal)
    c_bal.font = font_bold
    c_bal.fill = light_blue_fill
    c_bal.number_format = '#,##0.00'
    c_bal.alignment = Alignment(horizontal="right", vertical="center")

    for c in range(1, 8):
        ws.cell(row=r_idx, column=c).border = summary_border
    ws.row_dimensions[r_idx].height = 22
    r_idx += 1

    # 5. Section 2: EMI Schedule Table - SECOND
    r_idx += 1
    ws.merge_cells(f"A{r_idx}:G{r_idx}")
    ws[f"A{r_idx}"] = "2. 12-MONTH EMI AMORTIZATION SCHEDULE"
    ws[f"A{r_idx}"].font = font_section
    ws[f"A{r_idx}"].fill = header_section_fill
    ws[f"A{r_idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r_idx].height = 20
    r_idx += 1

    headers = ["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (Rs.)", "INTEREST (Rs.)", "EMI AMOUNT (Rs.)"]
    for c_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=r_idx, column=c_idx, value=h)
        cell.font = font_header_white
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[r_idx].height = 22
    r_idx += 1

    tot_p = 0.0
    tot_i = 0.0
    tot_e = 0.0

    if schedule_df is not None and hasattr(schedule_df, 'empty') and not schedule_df.empty:
        for _, row in schedule_df.iterrows():
            emi_no = row.get("EMI NOS", row.get("emi_number", 0))
            f_date = str(row.get("FROM DATE", row.get("from_date", "")))
            t_date = str(row.get("TO DATE", row.get("to_date", "")))
            d_date = str(row.get("DUE DATE", row.get("due_date", "")))
            p_amt = float(row.get("PRINCIPAL (Rs.)", row.get("principal_component", 0.0)))
            i_amt = float(row.get("INTEREST (Rs.)", row.get("interest_component", 0.0)))
            e_amt = float(row.get("EMI AMOUNT (Rs.)", row.get("emi_amount", 0.0)))

            tot_p += p_amt
            tot_i += i_amt
            tot_e += e_amt

            r_vals = [emi_no, f_date, t_date, d_date, p_amt, i_amt, e_amt]
            for col_idx, val in enumerate(r_vals, 1):
                c = ws.cell(row=r_idx, column=col_idx, value=val)
                c.font = font_normal
                c.border = thin_border
                if col_idx in [1, 2, 3, 4]:
                    c.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="right", vertical="center")
                    c.number_format = '#,##0.00'
            ws.row_dimensions[r_idx].height = 18
            r_idx += 1

    # Total Summary Footer for EMI
    ws.cell(row=r_idx, column=1, value="TOTAL SCHEDULE AMOUNT").font = font_bold
    ws.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=4)
    ws.cell(row=r_idx, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r_idx, column=1).fill = light_blue_fill

    c_tp = ws.cell(row=r_idx, column=5, value=tot_p)
    c_tp.font = font_bold
    c_tp.fill = light_blue_fill
    c_tp.number_format = '#,##0.00'
    c_tp.alignment = Alignment(horizontal="right", vertical="center")

    c_ti = ws.cell(row=r_idx, column=6, value=tot_i)
    c_ti.font = font_bold
    c_ti.fill = light_blue_fill
    c_ti.number_format = '#,##0.00'
    c_ti.alignment = Alignment(horizontal="right", vertical="center")

    c_te = ws.cell(row=r_idx, column=7, value=tot_e)
    c_te.font = font_bold
    c_te.fill = light_blue_fill
    c_te.number_format = '#,##0.00'
    c_te.alignment = Alignment(horizontal="right", vertical="center")

    for c in range(1, 8):
        ws.cell(row=r_idx, column=c).border = summary_border
    ws.row_dimensions[r_idx].height = 22

    # Column Widths
    col_widths = {1: 16, 2: 18, 3: 32, 4: 18, 5: 18, 6: 18, 7: 20}
    for col_idx, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


@cache_data
def create_loan_passbook_pdf(loan_data, schedule_df, repayments_df=None):
    """
    Generates a high-quality PDF Loan Passbook & Statement:
    - Company & Passbook Header
    - Borrower & Guarantor & Financial Details Block
    - Section 1: Customer Repayment Ledger (Debit / Credit) - FIRST
    - Section 2: 12-Month EMI Amortization Schedule Table - SECOND
    - Signatures block
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=10*mm, leftMargin=10*mm, 
                           topMargin=10*mm, bottomMargin=10*mm)
    elements = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'PLHeader',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        fontName='Helvetica-Bold',
        spaceAfter=1
    )
    sub_style = ParagraphStyle(
        'PLSub',
        parent=styles['Normal'],
        fontSize=7.5,
        textColor=colors.HexColor('#4b5563'),
        alignment=1,
        spaceAfter=1
    )
    title_style = ParagraphStyle(
        'PLTitle',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        fontName='Helvetica-Bold',
        spaceAfter=4
    )
    sec_title = ParagraphStyle(
        'PLSecTitle',
        parent=styles['Heading3'],
        fontSize=8.5,
        textColor=colors.HexColor('#1f4e78'),
        fontName='Helvetica-Bold',
        spaceBefore=3,
        spaceAfter=2
    )
    cell_bold = ParagraphStyle('CBold', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold')
    cell_norm = ParagraphStyle('CNorm', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica')
    cell_center = ParagraphStyle('CCenter', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=1)
    cell_right = ParagraphStyle('CRight', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=2)
    th_style = ParagraphStyle('CTH', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)

    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Paragraph("6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", sub_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Ph: 0471-2994535", sub_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph("LOAN PASSBOOK & STATEMENT OF ACCOUNT", title_style))
    elements.append(Spacer(1, 2))

    # Info grid
    info_table_data = [
        [
            Paragraph("<b>Loan A/c No:</b>", cell_bold), Paragraph(str(loan_data.get("loan_no", "")), cell_bold),
            Paragraph("<b>Status:</b>", cell_bold), Paragraph(str(loan_data.get("status", "ACTIVE")), cell_bold)
        ],
        [
            Paragraph("<b>Borrower Name:</b>", cell_bold), Paragraph(str(loan_data.get("party_name", "")), cell_norm),
            Paragraph("<b>Member Acc:</b>", cell_bold), Paragraph(str(loan_data.get("account_no", "N/A")), cell_norm)
        ],
        [
            Paragraph("<b>Address:</b>", cell_bold), Paragraph(str(loan_data.get("address", "")), cell_norm),
            Paragraph("<b>Mobile No:</b>", cell_bold), Paragraph(str(loan_data.get("mobile", "")), cell_norm)
        ],
        [
            Paragraph("<b>Guarantor / Surety:</b>", cell_bold), Paragraph(str(loan_data.get("guarantor_name", "")), cell_norm),
            Paragraph("<b>Relation / Ph:</b>", cell_bold), Paragraph(f"{loan_data.get('guarantor_relation', '')} | {loan_data.get('guarantor_phone', '')}", cell_norm)
        ],
        [
            Paragraph("<b>Principal Amount:</b>", cell_bold), Paragraph(f"₹{float(loan_data.get('loan_amount', 0)):,.2f}", cell_bold),
            Paragraph("<b>Monthly EMI:</b>", cell_bold), Paragraph(f"₹{float(loan_data.get('total_emi', 0)):,.2f}", cell_bold)
        ],
        [
            Paragraph("<b>Interest Rate:</b>", cell_bold), Paragraph(f"{loan_data.get('interest_rate', 12)}% Flat p.a.", cell_norm),
            Paragraph("<b>Total Repayable:</b>", cell_bold), Paragraph(f"₹{float(loan_data.get('total_amount', 0)):,.2f}", cell_bold)
        ],
        [
            Paragraph("<b>Loan Period:</b>", cell_bold), Paragraph(f"{loan_data.get('loan_from', '')} to {loan_data.get('loan_to', '')} ({loan_data.get('duration', '12 Months')})", cell_norm),
            Paragraph("<b>First / Last Due:</b>", cell_bold), Paragraph(f"{loan_data.get('first_emi_due', '')} / {loan_data.get('last_emi_due', '')}", cell_norm)
        ]
    ]

    t_info = Table(info_table_data, colWidths=[35*mm, 60*mm, 35*mm, 64*mm])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafd')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 3))

    # Section 1: Customer Repayment Ledger (Debit / Credit) - FIRST
    ledger_rows = extract_or_build_ledger_rows(loan_data, repayments_df)
    elements.append(Paragraph("<b>1. CUSTOMER REPAYMENT LEDGER & STATEMENT (DEBIT / CREDIT)</b>", sec_title))
    
    rep_data = [[
        Paragraph("Date", th_style),
        Paragraph("Voucher No", th_style),
        Paragraph("Particulars / Narration", th_style),
        Paragraph("Mode", th_style),
        Paragraph("Debit (₹)", th_style),
        Paragraph("Credit (₹)", th_style),
        Paragraph("Balance (₹)", th_style)
    ]]

    tot_dr = 0.0
    tot_cr = 0.0
    closing_bal = 0.0

    for d_val, v_val, p_val, m_val, dr_val, cr_val, bal_val in ledger_rows:
        tot_dr += dr_val
        tot_cr += cr_val
        closing_bal = bal_val

        rep_data.append([
            Paragraph(str(d_val), cell_center),
            Paragraph(str(v_val), cell_center),
            Paragraph(str(p_val), cell_norm),
            Paragraph(str(m_val), cell_center),
            Paragraph(f"{dr_val:,.2f}" if dr_val > 0 else "-", cell_right),
            Paragraph(f"{cr_val:,.2f}" if cr_val > 0 else "-", cell_right),
            Paragraph(f"{bal_val:,.2f}", cell_right)
        ])

    rep_data.append([
        Paragraph("<b>TOTAL / CLOSING DUE</b>", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph(f"<b>{tot_dr:,.2f}</b>", cell_right),
        Paragraph(f"<b>{tot_cr:,.2f}</b>", cell_right),
        Paragraph(f"<b>{closing_bal:,.2f}</b>", cell_right)
    ])

    t_rep = Table(rep_data, colWidths=[20*mm, 24*mm, 52*mm, 20*mm, 26*mm, 26*mm, 26*mm])
    t_rep.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#ebf5fb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_rep)
    elements.append(Spacer(1, 3))

    # Section 2: EMI Schedule Table - SECOND
    elements.append(Paragraph("<b>2. 12-MONTH EMI AMORTIZATION SCHEDULE</b>", sec_title))
    sched_data = [[
        Paragraph("EMI #", th_style),
        Paragraph("From Date", th_style),
        Paragraph("To Date", th_style),
        Paragraph("Due Date", th_style),
        Paragraph("Principal (₹)", th_style),
        Paragraph("Interest (₹)", th_style),
        Paragraph("EMI Total (₹)", th_style)
    ]]

    tot_p, tot_i, tot_e = 0.0, 0.0, 0.0
    if schedule_df is not None and hasattr(schedule_df, 'empty') and not schedule_df.empty:
        for _, row in schedule_df.iterrows():
            emi_no = str(row.get("EMI NOS", row.get("emi_number", 0)))
            f_date = str(row.get("FROM DATE", row.get("from_date", "")))
            t_date = str(row.get("TO DATE", row.get("to_date", "")))
            d_date = str(row.get("DUE DATE", row.get("due_date", "")))
            p_amt = float(row.get("PRINCIPAL (Rs.)", row.get("principal_component", 0.0)))
            i_amt = float(row.get("INTEREST (Rs.)", row.get("interest_component", 0.0)))
            e_amt = float(row.get("EMI AMOUNT (Rs.)", row.get("emi_amount", 0.0)))

            tot_p += p_amt
            tot_i += i_amt
            tot_e += e_amt

            sched_data.append([
                Paragraph(emi_no, cell_center),
                Paragraph(f_date, cell_center),
                Paragraph(t_date, cell_center),
                Paragraph(d_date, cell_center),
                Paragraph(f"{p_amt:,.2f}", cell_right),
                Paragraph(f"{i_amt:,.2f}", cell_right),
                Paragraph(f"{e_amt:,.2f}", cell_right)
            ])

    # Footer Row
    sched_data.append([
        Paragraph("<b>TOTAL</b>", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph(f"<b>{tot_p:,.2f}</b>", cell_right),
        Paragraph(f"<b>{tot_i:,.2f}</b>", cell_right),
        Paragraph(f"<b>{tot_e:,.2f}</b>", cell_right)
    ])

    t_sched = Table(sched_data, colWidths=[14*mm, 28*mm, 28*mm, 28*mm, 32*mm, 32*mm, 32*mm])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#ebf5fb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_sched)
    elements.append(Spacer(1, 6))

    # Signature Block
    sig_data = [
        [Paragraph("<b>Borrower Signature</b>", cell_center), Paragraph("<b>Guarantor Signature</b>", cell_center), Paragraph("<b>Authorized Signatory / Manager</b>", cell_center)]
    ]
    t_sig = Table(sig_data, colWidths=[63*mm, 63*mm, 68*mm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


@cache_data
def create_loan_agreement_pdf(loan_data, schedule_df):
    """
    Generates an official Legal Loan Agreement, Surety Undertaking Deed & Demand Promissory Note PDF.
    Supports both Original Sanctions and Renewal Agreements (Cycle #X).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=10*mm, leftMargin=10*mm, 
                           topMargin=10*mm, bottomMargin=10*mm)
    elements = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'AgreeHeader',
        parent=styles['Heading1'],
        fontSize=13,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        fontName='Helvetica-Bold',
        spaceAfter=2
    )
    sub_style = ParagraphStyle(
        'AgreeSub',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#4b5563'),
        alignment=1,
        spaceAfter=1
    )
    title_style = ParagraphStyle(
        'AgreeTitle',
        parent=styles['Heading2'],
        fontSize=10.5,
        textColor=colors.HexColor('#1f4e78'),
        alignment=1,
        fontName='Helvetica-Bold',
        spaceAfter=4
    )
    sec_title = ParagraphStyle(
        'AgreeSecTitle',
        parent=styles['Heading3'],
        fontSize=9,
        textColor=colors.HexColor('#1f4e78'),
        fontName='Helvetica-Bold',
        spaceBefore=4,
        spaceAfter=2
    )
    body_style = ParagraphStyle(
        'AgreeBody',
        parent=styles['Normal'],
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#222222'),
        alignment=4
    )
    cell_bold = ParagraphStyle('CBold', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold')
    cell_norm = ParagraphStyle('CNorm', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica')
    cell_center = ParagraphStyle('CCenter', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=1)
    cell_right = ParagraphStyle('CRight', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=2)
    th_style = ParagraphStyle('CTH', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)

    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Paragraph("Reg. Office: 6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", sub_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Phone: 0471-2994535", sub_style))
    elements.append(Spacer(1, 2))

    ren_cnt = int(loan_data.get("renewal_count", 0) or 0)
    if ren_cnt > 0:
        doc_title = f"RENEWAL PERSONAL LOAN AGREEMENT, SURETY BOND & EXTENSION DEED (CYCLE #{ren_cnt})"
    else:
        doc_title = "PERSONAL LOAN AGREEMENT, SURETY BOND & DEMAND PROMISSORY NOTE"
    elements.append(Paragraph(doc_title, title_style))
    elements.append(Spacer(1, 3))

    # Parties Block
    parties_data = [
        [
            Paragraph("<b>LENDER:</b>", cell_bold),
            Paragraph("<b>M/s AARSHA NIDHI LIMITED</b>, a Nidhi Company incorporated under the Companies Act, 2013, having its registered office at Balaramapuram, Trivandrum.", cell_norm)
        ],
        [
            Paragraph("<b>BORROWER:</b>", cell_bold),
            Paragraph(f"<b>{loan_data.get('party_name', '')}</b> (Member Acc: <b>{loan_data.get('account_no', 'N/A')}</b>)<br/>Address: {loan_data.get('address', '')} | Mobile: {loan_data.get('mobile', '')}", cell_norm)
        ],
        [
            Paragraph("<b>SURETY / GUARANTOR:</b>", cell_bold),
            Paragraph(f"<b>{loan_data.get('guarantor_name', '')}</b> ({loan_data.get('guarantor_relation', 'Surety')})<br/>Address: {loan_data.get('guarantor_address', '')} | Mobile: {loan_data.get('guarantor_phone', '')}", cell_norm)
        ]
    ]
    t_parties = Table(parties_data, colWidths=[40*mm, 150*mm])
    t_parties.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafd')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_parties)
    elements.append(Spacer(1, 3))

    # Loan Financial Terms Grid
    princ_val = float(loan_data.get("loan_amount", 0.0) or 0.0)
    int_rate_val = float(loan_data.get("interest_rate", 12.0) or 12.0)
    tot_int_val = float(loan_data.get("total_interest", princ_val * (int_rate_val/100.0)) or 0.0)
    tot_rep_val = float(loan_data.get("total_amount", princ_val + tot_int_val) or 0.0)
    emi_val = float(loan_data.get("total_emi", 0.0) or 0.0)
    p_emi_val = float(loan_data.get("principal_emi", 0.0) or 0.0)
    i_emi_val = float(loan_data.get("interest_emi", 0.0) or 0.0)
    tenure_str = str(loan_data.get("duration", "12 Months"))
    loan_no_str = str(loan_data.get("loan_no", ""))
    sanc_date_str = str(loan_data.get("sanction_date", loan_data.get("loan_from", "")))

    terms_data = [
        [
            Paragraph("<b>Loan A/c No:</b>", cell_bold), Paragraph(f"<b>{loan_no_str}</b>", cell_bold),
            Paragraph("<b>Execution Date:</b>", cell_bold), Paragraph(sanc_date_str, cell_norm)
        ],
        [
            Paragraph("<b>Sanctioned Principal:</b>", cell_bold), Paragraph(f"<b>₹{princ_val:,.2f}</b>", cell_bold),
            Paragraph("<b>Agreed Interest:</b>", cell_bold), Paragraph(f"{int_rate_val}% Flat (₹{tot_int_val:,.2f})", cell_norm)
        ],
        [
            Paragraph("<b>Total Repayable Sum:</b>", cell_bold), Paragraph(f"<b>₹{tot_rep_val:,.2f}</b>", cell_bold),
            Paragraph("<b>Loan Tenure:</b>", cell_bold), Paragraph(tenure_str, cell_norm)
        ],
        [
            Paragraph("<b>Monthly EMI:</b>", cell_bold), Paragraph(f"<b>₹{emi_val:,.2f}</b> (P: ₹{p_emi_val:,.2f} + I: ₹{i_emi_val:,.2f})", cell_norm),
            Paragraph("<b>Period & Due Dates:</b>", cell_bold), Paragraph(f"{loan_data.get('loan_from', '')} to {loan_data.get('loan_to', '')}", cell_norm)
        ]
    ]
    t_terms = Table(terms_data, colWidths=[38*mm, 57*mm, 38*mm, 57*mm])
    t_terms.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafd')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_terms)
    elements.append(Spacer(1, 3))

    # Amortization Table
    elements.append(Paragraph("<b>REPAYMENT INSTALLMENT SCHEDULE</b>", sec_title))
    sched_data = [[
        Paragraph("EMI #", th_style),
        Paragraph("From Date", th_style),
        Paragraph("To Date", th_style),
        Paragraph("Due Date", th_style),
        Paragraph("Principal (₹)", th_style),
        Paragraph("Interest (₹)", th_style),
        Paragraph("Total EMI (₹)", th_style)
    ]]

    if hasattr(schedule_df, 'empty') and not schedule_df.empty:
        for _, row in schedule_df.iterrows():
            emi_no = str(row.get("EMI NOS", row.get("emi_number", 0)))
            f_date = str(row.get("FROM DATE", row.get("from_date", "")))
            t_date = str(row.get("TO DATE", row.get("to_date", "")))
            d_date = str(row.get("DUE DATE", row.get("due_date", "")))
            p_amt = float(row.get("PRINCIPAL (Rs.)", row.get("principal_component", 0.0)))
            i_amt = float(row.get("INTEREST (Rs.)", row.get("interest_component", 0.0)))
            e_amt = float(row.get("EMI AMOUNT (Rs.)", row.get("emi_amount", 0.0)))
            sched_data.append([
                Paragraph(emi_no, cell_center),
                Paragraph(f_date, cell_center),
                Paragraph(t_date, cell_center),
                Paragraph(d_date, cell_center),
                Paragraph(f"{p_amt:,.2f}", cell_right),
                Paragraph(f"{i_amt:,.2f}", cell_right),
                Paragraph(f"{e_amt:,.2f}", cell_right)
            ])

    t_sched = Table(sched_data, colWidths=[14*mm, 28*mm, 28*mm, 28*mm, 31*mm, 30*mm, 31*mm])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_sched)
    elements.append(Spacer(1, 3))

    # Covenants & Undertakings
    elements.append(Paragraph("<b>LEGAL COVENANTS, SURETY UNDERTAKING & DEMAND PROMISSORY NOTE</b>", sec_title))
    cov_text = (
        "1. <b>Joint & Several Liability:</b> The Borrower and the Surety/Guarantor hereby jointly and severally promise to pay on demand to Aarsha Nidhi Limited the total repayable amount with accrued interest as per the above schedule.<br/>"
        "2. <b>Lien & Right of Set-Off:</b> The Lender shall have a paramount lien on all deposits, shares, and assets of the Borrower and Guarantor.<br/>"
        "3. <b>Default:</b> In the event of default on any installment, the Lender reserves the right to declare the entire loan immediately due and initiate legal recovery proceedings.<br/>"
        "4. <b>Renewal / Rollover:</b> Upon completion of the tenure, any remaining unpaid principal may be renewed into a fresh term upon mutual agreement with re-computed interest."
    )
    elements.append(Paragraph(cov_text, body_style))
    elements.append(Spacer(1, 4))

    # Signatures
    sig_table = Table([
        [
            Paragraph("____________________________<br/><b>Signature of Borrower</b><br/>(Thumb Impression / Signed)", cell_center),
            Paragraph("____________________________<br/><b>Signature of Surety / Guarantor</b><br/>(Co-Obligant)", cell_center),
            Paragraph("____________________________<br/><b>For AARSHA NIDHI LIMITED</b><br/>(Authorized Signatory / Secretary)", cell_center)
        ]
    ], colWidths=[63*mm, 63*mm, 64*mm])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


@cache_data
def create_gold_loan_passbook_excel(loan_data, schedule_df, repayments_df=None):
    """
    Generates a Gold Loan Passbook in Microsoft Excel (.xlsx) format:
    - Company & Gold Loan Header
    - Customer & Pledged Gold Custody / Valuation Details Block
    - Financial Terms & EMI Summary Block
    - Section 1: Customer Repayment Ledger (Debit / Credit Transactions) - FIRST
    - Section 2: 12-Month EMI Amortization Schedule Table - SECOND
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return b""

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "GOLD LOAN STATEMENT"
    ws.views.sheetView[0].showGridLines = True

    # Styling Palette
    navy_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    light_blue_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    soft_gray_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    header_section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    font_title = Font(name="Segoe UI", size=14, bold=True, color="1F4E78")
    font_sub = Font(name="Segoe UI", size=9, color="4B5563")
    font_header_white = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Segoe UI", size=9.5, bold=True, color="000000")
    font_normal = Font(name="Segoe UI", size=9.5, color="000000")
    font_section = Font(name="Segoe UI", size=10.5, bold=True, color="1F4E78")

    thin_side = Side(border_style="thin", color="D0D5DD")
    double_bottom_side = Side(border_style="double", color="1F4E78")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    summary_border = Border(top=thin_side, bottom=double_bottom_side, left=thin_side, right=thin_side)

    # 1. Company Header
    ws.merge_cells("A1:G1")
    ws["A1"] = "AARSHA NIDHI LIMITED"
    ws["A1"].font = font_title
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    ws.merge_cells("A2:G2")
    ws["A2"] = "6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501"
    ws["A2"].font = font_sub
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 14

    ws.merge_cells("A3:G3")
    ws["A3"] = "CIN: U65990KL2021PLN069978 | Ph: 0471-2994535"
    ws["A3"].font = font_sub
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 14

    ws.merge_cells("A4:G4")
    ws["A4"] = "GOLD LOAN STATEMENT OF ACCOUNT & PAWN PASSBOOK"
    ws["A4"].font = Font(name="Segoe UI", size=12, bold=True, color="FFFFFF")
    ws["A4"].fill = navy_fill
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[4].height = 22

    # 2. Loan & Borrower Info Block
    p_name = str(loan_data.get("party_name", loan_data.get("customer_name", "")))
    p_acc = str(loan_data.get("account_no", "N/A"))
    p_mob = str(loan_data.get("mobile", loan_data.get("phone", "")))
    p_addr = str(loan_data.get("address", ""))
    
    info_rows = [
        ("LOAN ACCOUNT NO", str(loan_data.get("loan_no", "")), "STATUS", str(loan_data.get("status", "ACTIVE"))),
        ("LOAN PARTY NAME", p_name, "MEMBER ACC NO", p_acc),
        ("ADDRESS", p_addr, "MOBILE NUMBER", p_mob),
        ("SAFE PACKET NO", str(loan_data.get("vault_packet_no", "")), "LOCKER NO", str(loan_data.get("locker_no", "LOCKER-01"))),
        ("PLDGD ORNAMENTS", str(loan_data.get("ornament_details", "22K Gold Jewels")), "NET GOLD WEIGHT", f"{float(loan_data.get('net_weight', 0)):.3f} g (Gross: {float(loan_data.get('gross_weight', 0)):.3f}g)"),
        ("CERTIFIED APPRAISER", str(loan_data.get("appraiser_name", "Approved Nidhi Appraiser")), "MARKET VALUATION", f"Rs. {float(loan_data.get('market_value', 0)):,.2f} (@ Rs.{float(loan_data.get('gold_rate_per_gram', 6500)):,.2f}/g)"),
    ]

    r_idx = 6
    for lbl1, val1, lbl2, val2 in info_rows:
        ws.cell(row=r_idx, column=1, value=lbl1).font = font_bold
        ws.cell(row=r_idx, column=1).fill = soft_gray_fill
        ws.cell(row=r_idx, column=2, value=val1).font = font_normal
        ws.merge_cells(start_row=r_idx, start_column=2, end_row=r_idx, end_column=4)

        ws.cell(row=r_idx, column=5, value=lbl2).font = font_bold
        ws.cell(row=r_idx, column=5).fill = soft_gray_fill
        ws.cell(row=r_idx, column=6, value=val2).font = font_normal
        ws.merge_cells(start_row=r_idx, start_column=6, end_row=r_idx, end_column=7)
        ws.row_dimensions[r_idx].height = 19
        r_idx += 1

    # 3. Financial Breakdown Block
    r_idx += 1
    ws.merge_cells(f"A{r_idx}:G{r_idx}")
    ws[f"A{r_idx}"] = "LOAN FINANCIAL TERMS & EMI SUMMARY"
    ws[f"A{r_idx}"].font = font_section
    ws[f"A{r_idx}"].fill = light_blue_fill
    ws[f"A{r_idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r_idx].height = 20
    r_idx += 1

    p_amt = float(loan_data.get("loan_amount", loan_data.get("principal_amount", 0)))
    tot_int = float(loan_data.get("total_interest", 0))
    tot_rep = float(loan_data.get("total_amount", loan_data.get("total_repayable", p_amt + tot_int)))
    p_emi_val = float(loan_data.get("principal_emi", loan_data.get("monthly_principal_emi", 0)))
    i_emi_val = float(loan_data.get("interest_emi", loan_data.get("monthly_interest_emi", 0)))
    t_emi_val = float(loan_data.get("total_emi", loan_data.get("installment_amount", p_emi_val + i_emi_val)))
    int_rate_str = str(loan_data.get("interest_rate", 12))

    fin_rows = [
        ("LOAN AMOUNT", p_amt, "PRINCIPAL EMI", p_emi_val),
        (f"INTEREST ({int_rate_str}%)", tot_int, "INTEREST EMI", i_emi_val),
        ("TOTAL AMOUNT", tot_rep, "TOTAL MONTHLY EMI", t_emi_val),
        ("LOAN DATE", str(loan_data.get("loan_date", loan_data.get("sanction_date", ""))), "DURATION", str(loan_data.get("duration", f"{loan_data.get('tenure_months', 12)} Months"))),
        ("LOAN FROM", str(loan_data.get("loan_from", loan_data.get("sanction_date", ""))), "LOAN TO", str(loan_data.get("loan_to", ""))),
        ("FIRST EMI DUE", str(loan_data.get("first_emi_due", "")), "LAST EMI DUE", str(loan_data.get("last_emi_due", ""))),
    ]

    for lbl1, val1, lbl2, val2 in fin_rows:
        ws.cell(row=r_idx, column=1, value=lbl1).font = font_bold
        ws.cell(row=r_idx, column=1).fill = soft_gray_fill
        
        c_val1 = ws.cell(row=r_idx, column=2, value=val1)
        c_val1.font = font_bold if isinstance(val1, (int, float)) else font_normal
        if isinstance(val1, (int, float)):
            c_val1.number_format = '"Rs." #,##0.00'
        ws.merge_cells(start_row=r_idx, start_column=2, end_row=r_idx, end_column=4)

        ws.cell(row=r_idx, column=5, value=lbl2).font = font_bold
        ws.cell(row=r_idx, column=5).fill = soft_gray_fill
        
        c_val2 = ws.cell(row=r_idx, column=6, value=val2)
        c_val2.font = font_bold if isinstance(val2, (int, float)) else font_normal
        if isinstance(val2, (int, float)):
            c_val2.number_format = '"Rs." #,##0.00'
        ws.merge_cells(start_row=r_idx, start_column=6, end_row=r_idx, end_column=7)
        
        ws.row_dimensions[r_idx].height = 19
        r_idx += 1

    # 4. Section 1: Customer Repayment Ledger (Debit / Credit) - FIRST
    ledger_rows = extract_or_build_ledger_rows(loan_data, repayments_df)
    r_idx += 1
    ws.merge_cells(f"A{r_idx}:G{r_idx}")
    ws[f"A{r_idx}"] = "1. REPAYMENT TRANSACTIONS & CUSTOMER LEDGER (DEBIT / CREDIT)"
    ws[f"A{r_idx}"].font = font_section
    ws[f"A{r_idx}"].fill = header_section_fill
    ws[f"A{r_idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r_idx].height = 20
    r_idx += 1

    rep_headers = ["DATE", "VOUCHER NO", "PARTICULARS", "PAYMENT MODE", "DEBIT (Rs.)", "CREDIT (Rs.)", "BALANCE (Rs.)"]
    for c_idx, h in enumerate(rep_headers, 1):
        cell = ws.cell(row=r_idx, column=c_idx, value=h)
        cell.font = font_header_white
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[r_idx].height = 22
    r_idx += 1

    tot_dr = 0.0
    tot_cr = 0.0
    closing_bal = 0.0

    for d_val, v_val, p_val, m_val, dr_val, cr_val, bal_val in ledger_rows:
        tot_dr += dr_val
        tot_cr += cr_val
        closing_bal = bal_val

        r_vals = [d_val, v_val, p_val, m_val, dr_val, cr_val, bal_val]
        for col_idx, val in enumerate(r_vals, 1):
            c = ws.cell(row=r_idx, column=col_idx, value=val)
            c.font = font_normal
            c.border = thin_border
            if col_idx in [1, 2, 4]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 3:
                c.alignment = Alignment(horizontal="left", vertical="center")
            else:
                c.alignment = Alignment(horizontal="right", vertical="center")
                c.number_format = '#,##0.00'
        ws.row_dimensions[r_idx].height = 18
        r_idx += 1

    # Summary row for Repayments
    ws.cell(row=r_idx, column=1, value="TOTAL TRANSACTIONS & CLOSING DUE").font = font_bold
    ws.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=4)
    ws.cell(row=r_idx, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r_idx, column=1).fill = light_blue_fill

    c_dr = ws.cell(row=r_idx, column=5, value=tot_dr)
    c_dr.font = font_bold
    c_dr.fill = light_blue_fill
    c_dr.number_format = '#,##0.00'
    c_dr.alignment = Alignment(horizontal="right", vertical="center")

    c_cr = ws.cell(row=r_idx, column=6, value=tot_cr)
    c_cr.font = font_bold
    c_cr.fill = light_blue_fill
    c_cr.number_format = '#,##0.00'
    c_cr.alignment = Alignment(horizontal="right", vertical="center")

    c_bal = ws.cell(row=r_idx, column=7, value=closing_bal)
    c_bal.font = font_bold
    c_bal.fill = light_blue_fill
    c_bal.number_format = '#,##0.00'
    c_bal.alignment = Alignment(horizontal="right", vertical="center")

    for c in range(1, 8):
        ws.cell(row=r_idx, column=c).border = summary_border
    ws.row_dimensions[r_idx].height = 22
    r_idx += 1

    # 5. Section 2: EMI Schedule Table - SECOND
    r_idx += 1
    ws.merge_cells(f"A{r_idx}:G{r_idx}")
    ws[f"A{r_idx}"] = "2. 12-MONTH EMI AMORTIZATION SCHEDULE"
    ws[f"A{r_idx}"].font = font_section
    ws[f"A{r_idx}"].fill = header_section_fill
    ws[f"A{r_idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r_idx].height = 20
    r_idx += 1

    headers = ["EMI NOS", "FROM DATE", "TO DATE", "DUE DATE", "PRINCIPAL (Rs.)", "INTEREST (Rs.)", "EMI AMOUNT (Rs.)"]
    for c_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=r_idx, column=c_idx, value=h)
        cell.font = font_header_white
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[r_idx].height = 22
    r_idx += 1

    tot_p = 0.0
    tot_i = 0.0
    tot_e = 0.0

    if hasattr(schedule_df, 'empty') and not schedule_df.empty:
        for _, row in schedule_df.iterrows():
            emi_no = row.get("EMI NOS", row.get("emi_number", 0))
            f_date = str(row.get("FROM DATE", row.get("from_date", "")))
            t_date = str(row.get("TO DATE", row.get("to_date", "")))
            d_date = str(row.get("DUE DATE", row.get("due_date", "")))
            p_comp = float(row.get("PRINCIPAL (Rs.)", row.get("principal_component", 0.0)))
            i_comp = float(row.get("INTEREST (Rs.)", row.get("interest_component", 0.0)))
            e_comp = float(row.get("EMI AMOUNT (Rs.)", row.get("emi_amount", 0.0)))

            tot_p += p_comp
            tot_i += i_comp
            tot_e += e_comp

            r_vals = [emi_no, f_date, t_date, d_date, p_comp, i_comp, e_comp]
            for col_idx, val in enumerate(r_vals, 1):
                c = ws.cell(row=r_idx, column=col_idx, value=val)
                c.font = font_normal
                c.border = thin_border
                if col_idx in [1, 2, 3, 4]:
                    c.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="right", vertical="center")
                    c.number_format = '#,##0.00'
            ws.row_dimensions[r_idx].height = 18
            r_idx += 1

    # Total Summary Footer for EMI
    ws.cell(row=r_idx, column=1, value="TOTAL SCHEDULE AMOUNT").font = font_bold
    ws.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=4)
    ws.cell(row=r_idx, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r_idx, column=1).fill = light_blue_fill

    c_tp = ws.cell(row=r_idx, column=5, value=tot_p)
    c_tp.font = font_bold
    c_tp.fill = light_blue_fill
    c_tp.number_format = '#,##0.00'
    c_tp.alignment = Alignment(horizontal="right", vertical="center")

    c_ti = ws.cell(row=r_idx, column=6, value=tot_i)
    c_ti.font = font_bold
    c_ti.fill = light_blue_fill
    c_ti.number_format = '#,##0.00'
    c_ti.alignment = Alignment(horizontal="right", vertical="center")

    c_te = ws.cell(row=r_idx, column=7, value=tot_e)
    c_te.font = font_bold
    c_te.fill = light_blue_fill
    c_te.number_format = '#,##0.00'
    c_te.alignment = Alignment(horizontal="right", vertical="center")

    for c in range(1, 8):
        ws.cell(row=r_idx, column=c).border = summary_border
    ws.row_dimensions[r_idx].height = 22

    # Column Widths
    col_widths = {1: 16, 2: 18, 3: 32, 4: 18, 5: 18, 6: 18, 7: 20}
    for col_idx, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


@cache_data
def create_gold_loan_agreement_pdf(loan_data, schedule_df=None):
    """
    Generates an official Gold Loan Pawn Deed, Pledge Agreement & Demand Promissory Note PDF.
    Supports both Original Sanctions and Renewal Deeds (Cycle #X) with complete 12-Month EMI Schedule.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=10*mm, leftMargin=10*mm, 
                           topMargin=10*mm, bottomMargin=10*mm)
    elements = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle('GLHeader', parent=styles['Heading1'], fontSize=13, textColor=colors.HexColor('#1f4e78'), alignment=1, fontName='Helvetica-Bold', spaceAfter=2)
    sub_style = ParagraphStyle('GLSub', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#4b5563'), alignment=1, spaceAfter=1)
    title_style = ParagraphStyle('GLTitle', parent=styles['Heading2'], fontSize=10.5, textColor=colors.HexColor('#1f4e78'), alignment=1, fontName='Helvetica-Bold', spaceAfter=4)
    sec_title = ParagraphStyle('GLSecTitle', parent=styles['Heading3'], fontSize=9, textColor=colors.HexColor('#1f4e78'), fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=2)
    body_style = ParagraphStyle('GLBody', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#222222'), alignment=4)
    cell_bold = ParagraphStyle('CBold', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold')
    cell_norm = ParagraphStyle('CNorm', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica')
    cell_center = ParagraphStyle('CCenter', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=1)
    cell_right = ParagraphStyle('CRight', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=2)
    th_style = ParagraphStyle('CTH', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)

    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Paragraph("Reg. Office: 6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", sub_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Phone: 0471-2994535", sub_style))
    elements.append(Spacer(1, 2))

    ren_cnt = int(loan_data.get("renewal_count", 0) or 0)
    if ren_cnt > 0:
        doc_title = f"RENEWED GOLD LOAN PLEDGE DEED & RE-APPRAISAL ACKNOWLEDGMENT (CYCLE #{ren_cnt})"
    else:
        doc_title = "GOLD LOAN PAWN DEED, PLEDGE AGREEMENT & DEMAND PROMISSORY NOTE"
    elements.append(Paragraph(doc_title, title_style))
    elements.append(Spacer(1, 3))

    # Parties Block
    parties_data = [
        [
            Paragraph("<b>LENDER / PAWNEE:</b>", cell_bold),
            Paragraph("<b>M/s AARSHA NIDHI LIMITED</b>, Balaramapuram, Trivandrum.", cell_norm)
        ],
        [
            Paragraph("<b>BORROWER / PLEDGOR:</b>", cell_bold),
            Paragraph(f"<b>{loan_data.get('party_name', loan_data.get('customer_name', ''))}</b> (Member Acc: <b>{loan_data.get('account_no', 'N/A')}</b>)<br/>Address: {loan_data.get('address', '')} | Mobile: {loan_data.get('phone', loan_data.get('mobile', ''))}", cell_norm)
        ],
        [
            Paragraph("<b>SAFE VAULT CUSTODY:</b>", cell_bold),
            Paragraph(f"Packet No: <b>{loan_data.get('vault_packet_no', '')}</b> | Locker: <b>{loan_data.get('locker_no', '')}</b> | Certified Appraiser: <b>{loan_data.get('appraiser_name', 'Approved Nidhi Appraiser')}</b>", cell_norm)
        ]
    ]
    t_parties = Table(parties_data, colWidths=[45*mm, 145*mm])
    t_parties.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafd')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_parties)
    elements.append(Spacer(1, 3))

    # Pledged Ornaments Inventory
    elements.append(Paragraph("<b>PLEDGED GOLD ORNAMENTS & VALUATION INVENTORY</b>", sec_title))
    inv_data = [
        [
            Paragraph("Ornament Description", th_style),
            Paragraph("Item Count", th_style),
            Paragraph("Gross Wt (g)", th_style),
            Paragraph("Dross/Stone (g)", th_style),
            Paragraph("Net Wt (g)", th_style),
            Paragraph("Gold Rate (₹/g)", th_style),
            Paragraph("Market Value (₹)", th_style)
        ],
        [
            Paragraph(str(loan_data.get("ornament_details", "22K Gold Jewels")), cell_norm),
            Paragraph(str(loan_data.get("item_count", "1")), cell_center),
            Paragraph(f"{float(loan_data.get('gross_weight', 0)):.3f} g", cell_center),
            Paragraph(f"{float(loan_data.get('stone_deduction', 0)):.3f} g", cell_center),
            Paragraph(f"<b>{float(loan_data.get('net_weight', 0)):.3f} g</b>", cell_center),
            Paragraph(f"₹{float(loan_data.get('gold_rate_per_gram', loan_data.get('gold_rate', 0))):,.2f}", cell_right),
            Paragraph(f"<b>₹{float(loan_data.get('market_value', 0)):,.2f}</b>", cell_right)
        ]
    ]
    t_inv = Table(inv_data, colWidths=[55*mm, 20*mm, 22*mm, 23*mm, 22*mm, 23*mm, 25*mm])
    t_inv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_inv)
    elements.append(Spacer(1, 3))

    # Loan Financial Terms
    p_amt = float(loan_data.get("loan_amount", loan_data.get("principal_amount", 0.0)) or 0.0)
    int_rate_val = float(loan_data.get("interest_rate", 12.0) or 12.0)
    tot_int_val = float(loan_data.get("total_interest", p_amt * (int_rate_val / 100.0)) or 0.0)
    tot_rep_val = float(loan_data.get("total_amount", loan_data.get("total_repayable", p_amt + tot_int_val)) or 0.0)
    emi_val = float(loan_data.get("total_emi", loan_data.get("installment_amount", 0.0)) or 0.0)
    p_emi_val = float(loan_data.get("principal_emi", loan_data.get("monthly_principal_emi", 0.0)) or 0.0)
    i_emi_val = float(loan_data.get("interest_emi", loan_data.get("monthly_interest_emi", 0.0)) or 0.0)
    tenure_str = str(loan_data.get("duration", f"{loan_data.get('tenure_months', 12)} Months"))
    loan_no_str = str(loan_data.get("loan_no", ""))
    sanc_date_str = str(loan_data.get("sanction_date", loan_data.get("loan_date", "")))

    terms_data = [
        [
            Paragraph("<b>Loan Number:</b>", cell_bold), Paragraph(f"<b>{loan_no_str}</b>", cell_bold),
            Paragraph("<b>Execution Date:</b>", cell_bold), Paragraph(sanc_date_str, cell_norm)
        ],
        [
            Paragraph("<b>Sanctioned Principal:</b>", cell_bold), Paragraph(f"<b>₹{p_amt:,.2f}</b>", cell_bold),
            Paragraph("<b>Agreed Interest:</b>", cell_bold), Paragraph(f"{int_rate_val}% Flat (₹{tot_int_val:,.2f})", cell_norm)
        ],
        [
            Paragraph("<b>Total Repayable Sum:</b>", cell_bold), Paragraph(f"<b>₹{tot_rep_val:,.2f}</b>", cell_bold),
            Paragraph("<b>Loan Tenure:</b>", cell_bold), Paragraph(tenure_str, cell_norm)
        ],
        [
            Paragraph("<b>Monthly EMI:</b>", cell_bold), Paragraph(f"<b>₹{emi_val:,.2f}</b> (P: ₹{p_emi_val:,.2f} + I: ₹{i_emi_val:,.2f})", cell_norm),
            Paragraph("<b>Period & Due Dates:</b>", cell_bold), Paragraph(f"{loan_data.get('loan_from', '')} to {loan_data.get('loan_to', '')}", cell_norm)
        ]
    ]
    t_terms = Table(terms_data, colWidths=[40*mm, 55*mm, 40*mm, 55*mm])
    t_terms.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafd')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_terms)
    elements.append(Spacer(1, 3))

    # Repayment Schedule Table
    if schedule_df is not None and hasattr(schedule_df, 'empty') and not schedule_df.empty:
        elements.append(Paragraph("<b>REPAYMENT INSTALLMENT SCHEDULE</b>", sec_title))
        sched_data = [[
            Paragraph("EMI #", th_style),
            Paragraph("From Date", th_style),
            Paragraph("To Date", th_style),
            Paragraph("Due Date", th_style),
            Paragraph("Principal (₹)", th_style),
            Paragraph("Interest (₹)", th_style),
            Paragraph("Total EMI (₹)", th_style)
        ]]

        for _, row in schedule_df.iterrows():
            emi_no = str(row.get("EMI NOS", row.get("emi_number", 0)))
            f_date = str(row.get("FROM DATE", row.get("from_date", "")))
            t_date = str(row.get("TO DATE", row.get("to_date", "")))
            d_date = str(row.get("DUE DATE", row.get("due_date", "")))
            p_val = float(row.get("PRINCIPAL (Rs.)", row.get("principal_component", 0.0)))
            i_val = float(row.get("INTEREST (Rs.)", row.get("interest_component", 0.0)))
            e_val = float(row.get("EMI AMOUNT (Rs.)", row.get("emi_amount", 0.0)))
            sched_data.append([
                Paragraph(emi_no, cell_center),
                Paragraph(f_date, cell_center),
                Paragraph(t_date, cell_center),
                Paragraph(d_date, cell_center),
                Paragraph(f"{p_val:,.2f}", cell_right),
                Paragraph(f"{i_val:,.2f}", cell_right),
                Paragraph(f"{e_val:,.2f}", cell_right)
            ])

        t_sched = Table(sched_data, colWidths=[14*mm, 28*mm, 28*mm, 28*mm, 31*mm, 30*mm, 31*mm])
        t_sched.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(t_sched)
        elements.append(Spacer(1, 3))

    # Terms & Conditions
    elements.append(Paragraph("<b>PLEDGE COVENANTS & DEMAND PROMISSORY NOTE</b>", sec_title))
    pawn_cov = (
        "1. <b>Pledge of Gold:</b> The Pledgor/Borrower declares that the pledged gold articles are their bona-fide absolute property and free from all encumbrances.<br/>"
        "2. <b>Repayment Obligation:</b> The Borrower agrees to repay the monthly EMI installment of ₹" + f"{emi_val:,.2f}" + " as per the above schedule.<br/>"
        "3. <b>Safe Custody:</b> The Lender warrants safe vault custody of the pledged ornaments.<br/>"
        "4. <b>Default & Auction Notice:</b> In case of non-payment upon tenure completion, the Lender reserves the right to issue statutory notice and auction the pledged gold to recover the outstanding balance."
    )
    elements.append(Paragraph(pawn_cov, body_style))
    elements.append(Spacer(1, 4))

    # Signatures
    sig_table = Table([
        [
            Paragraph("____________________________<br/><b>Signature of Borrower / Pledgor</b><br/>(Received Cash in Full)", cell_center),
            Paragraph("____________________________<br/><b>Certified Gold Appraiser</b><br/>(Weight & Purity Verified)", cell_center),
            Paragraph("____________________________<br/><b>For AARSHA NIDHI LIMITED</b><br/>(Authorized Signatory / Manager)", cell_center)
        ]
    ], colWidths=[63*mm, 63*mm, 64*mm])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


@cache_data
def create_gold_loan_passbook_pdf(loan_data, schedule_df, repayments_df=None):
    """
    Generates a high-resolution printable Gold Loan Passbook & Statement PDF:
    - Company & Gold Loan Header
    - Borrower & Pledged Gold Custody & Valuation Grid
    - Section 1: Customer Repayment Ledger (Debit / Credit Transactions) - FIRST
    - Section 2: 12-Month EMI Amortization Schedule Table - SECOND
    - Signatures Block
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=10*mm, leftMargin=10*mm, 
                           topMargin=10*mm, bottomMargin=10*mm)
    elements = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle('GLPHeader', parent=styles['Heading1'], fontSize=12, textColor=colors.HexColor('#1f4e78'), alignment=1, fontName='Helvetica-Bold', spaceAfter=1)
    sub_style = ParagraphStyle('GLPSub', parent=styles['Normal'], fontSize=7.5, textColor=colors.HexColor('#4b5563'), alignment=1, spaceAfter=1)
    title_style = ParagraphStyle('GLPTitle', parent=styles['Heading2'], fontSize=10, textColor=colors.HexColor('#1f4e78'), alignment=1, fontName='Helvetica-Bold', spaceAfter=4)
    sec_title = ParagraphStyle('GLPSecTitle', parent=styles['Heading3'], fontSize=8.5, textColor=colors.HexColor('#1f4e78'), fontName='Helvetica-Bold', spaceBefore=3, spaceAfter=2)
    cell_bold = ParagraphStyle('CBold', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold')
    cell_norm = ParagraphStyle('CNorm', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica')
    cell_center = ParagraphStyle('CCenter', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=1)
    cell_right = ParagraphStyle('CRight', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', alignment=2)
    th_style = ParagraphStyle('CTH', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)

    elements.append(Paragraph("AARSHA NIDHI LIMITED", header_style))
    elements.append(Paragraph("6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", sub_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Ph: 0471-2994535", sub_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph("GOLD LOAN STATEMENT & PAWN PASSBOOK", title_style))
    elements.append(Spacer(1, 2))

    p_name = str(loan_data.get("party_name", loan_data.get("customer_name", "")))
    p_acc = str(loan_data.get("account_no", "N/A"))
    p_addr = str(loan_data.get("address", ""))
    p_mob = str(loan_data.get("phone", loan_data.get("mobile", "")))

    p_amt = float(loan_data.get("loan_amount", loan_data.get("principal_amount", 0)))
    tot_int = float(loan_data.get("total_interest", 0))
    tot_rep = float(loan_data.get("total_amount", loan_data.get("total_repayable", p_amt + tot_int)))
    p_emi_val = float(loan_data.get("principal_emi", loan_data.get("monthly_principal_emi", 0)))
    i_emi_val = float(loan_data.get("interest_emi", loan_data.get("monthly_interest_emi", 0)))
    t_emi_val = float(loan_data.get("total_emi", loan_data.get("installment_amount", p_emi_val + i_emi_val)))

    # Info table
    info_table_data = [
        [
            Paragraph("<b>Loan A/c No:</b>", cell_bold), Paragraph(str(loan_data.get("loan_no", "")), cell_bold),
            Paragraph("<b>Status:</b>", cell_bold), Paragraph(str(loan_data.get("status", "ACTIVE")), cell_bold)
        ],
        [
            Paragraph("<b>Borrower Name:</b>", cell_bold), Paragraph(p_name, cell_norm),
            Paragraph("<b>Member Acc:</b>", cell_bold), Paragraph(p_acc, cell_norm)
        ],
        [
            Paragraph("<b>Address:</b>", cell_bold), Paragraph(p_addr, cell_norm),
            Paragraph("<b>Mobile No:</b>", cell_bold), Paragraph(p_mob, cell_norm)
        ],
        [
            Paragraph("<b>Safe Packet No:</b>", cell_bold), Paragraph(str(loan_data.get("vault_packet_no", "")), cell_norm),
            Paragraph("<b>Locker No:</b>", cell_bold), Paragraph(str(loan_data.get("locker_no", "")), cell_norm)
        ],
        [
            Paragraph("<b>Pledged Ornaments:</b>", cell_bold), Paragraph(str(loan_data.get("ornament_details", "")), cell_norm),
            Paragraph("<b>Net Weight:</b>", cell_bold), Paragraph(f"<b>{float(loan_data.get('net_weight', 0)):.3f} g</b> (Gross: {float(loan_data.get('gross_weight', 0)):.3f}g)", cell_norm)
        ],
        [
            Paragraph("<b>Market Valuation:</b>", cell_bold), Paragraph(f"₹{float(loan_data.get('market_value', 0)):,.2f} (@ ₹{float(loan_data.get('gold_rate_per_gram', 0)):,.2f}/g)", cell_norm),
            Paragraph("<b>Principal Loan:</b>", cell_bold), Paragraph(f"<b>₹{p_amt:,.2f}</b>", cell_bold)
        ],
        [
            Paragraph("<b>Total Interest:</b>", cell_bold), Paragraph(f"₹{tot_int:,.2f} ({loan_data.get('interest_rate', 12)}% Flat)", cell_norm),
            Paragraph("<b>Monthly EMI:</b>", cell_bold), Paragraph(f"<b>₹{t_emi_val:,.2f}</b> (P: ₹{p_emi_val:,.2f} + I: ₹{i_emi_val:,.2f})", cell_bold)
        ],
        [
            Paragraph("<b>Total Repayable:</b>", cell_bold), Paragraph(f"<b>₹{tot_rep:,.2f}</b>", cell_bold),
            Paragraph("<b>Loan Period:</b>", cell_bold), Paragraph(f"{loan_data.get('loan_from', '')} to {loan_data.get('loan_to', '')}", cell_norm)
        ]
    ]

    t_info = Table(info_table_data, colWidths=[35*mm, 60*mm, 35*mm, 64*mm])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafd')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 3))

    # Section 1: Customer Repayment Ledger (Debit / Credit) - FIRST
    ledger_rows = extract_or_build_ledger_rows(loan_data, repayments_df)
    elements.append(Paragraph("<b>1. CUSTOMER REPAYMENT LEDGER & STATEMENT (DEBIT / CREDIT)</b>", sec_title))
    
    rep_data = [[
        Paragraph("Date", th_style),
        Paragraph("Voucher No", th_style),
        Paragraph("Particulars / Narration", th_style),
        Paragraph("Mode", th_style),
        Paragraph("Debit (₹)", th_style),
        Paragraph("Credit (₹)", th_style),
        Paragraph("Balance (₹)", th_style)
    ]]

    tot_dr = 0.0
    tot_cr = 0.0
    closing_bal = 0.0

    for d_val, v_val, p_val, m_val, dr_val, cr_val, bal_val in ledger_rows:
        tot_dr += dr_val
        tot_cr += cr_val
        closing_bal = bal_val

        rep_data.append([
            Paragraph(str(d_val), cell_center),
            Paragraph(str(v_val), cell_center),
            Paragraph(str(p_val), cell_norm),
            Paragraph(str(m_val), cell_center),
            Paragraph(f"{dr_val:,.2f}" if dr_val > 0 else "-", cell_right),
            Paragraph(f"{cr_val:,.2f}" if cr_val > 0 else "-", cell_right),
            Paragraph(f"{bal_val:,.2f}", cell_right)
        ])

    rep_data.append([
        Paragraph("<b>TOTAL / CLOSING DUE</b>", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph(f"<b>{tot_dr:,.2f}</b>", cell_right),
        Paragraph(f"<b>{tot_cr:,.2f}</b>", cell_right),
        Paragraph(f"<b>{closing_bal:,.2f}</b>", cell_right)
    ])

    t_rep = Table(rep_data, colWidths=[20*mm, 24*mm, 52*mm, 20*mm, 26*mm, 26*mm, 26*mm])
    t_rep.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#ebf5fb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_rep)
    elements.append(Spacer(1, 3))

    # Section 2: EMI Schedule Table - SECOND
    elements.append(Paragraph("<b>2. 12-MONTH EMI AMORTIZATION SCHEDULE</b>", sec_title))
    sched_data = [[
        Paragraph("EMI #", th_style),
        Paragraph("From Date", th_style),
        Paragraph("To Date", th_style),
        Paragraph("Due Date", th_style),
        Paragraph("Principal (₹)", th_style),
        Paragraph("Interest (₹)", th_style),
        Paragraph("EMI Total (₹)", th_style)
    ]]

    tot_p, tot_i, tot_e = 0.0, 0.0, 0.0
    if hasattr(schedule_df, 'empty') and not schedule_df.empty:
        for _, row in schedule_df.iterrows():
            emi_no = str(row.get("EMI NOS", row.get("emi_number", 0)))
            f_date = str(row.get("FROM DATE", row.get("from_date", "")))
            t_date = str(row.get("TO DATE", row.get("to_date", "")))
            d_date = str(row.get("DUE DATE", row.get("due_date", "")))
            p_val = float(row.get("PRINCIPAL (Rs.)", row.get("principal_component", 0.0)))
            i_val = float(row.get("INTEREST (Rs.)", row.get("interest_component", 0.0)))
            e_val = float(row.get("EMI AMOUNT (Rs.)", row.get("emi_amount", 0.0)))

            tot_p += p_val
            tot_i += i_val
            tot_e += e_val

            sched_data.append([
                Paragraph(emi_no, cell_center),
                Paragraph(f_date, cell_center),
                Paragraph(t_date, cell_center),
                Paragraph(d_date, cell_center),
                Paragraph(f"{p_val:,.2f}", cell_right),
                Paragraph(f"{i_val:,.2f}", cell_right),
                Paragraph(f"{e_val:,.2f}", cell_right)
            ])

    sched_data.append([
        Paragraph("<b>TOTAL</b>", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph("-", cell_center),
        Paragraph(f"<b>{tot_p:,.2f}</b>", cell_right),
        Paragraph(f"<b>{tot_i:,.2f}</b>", cell_right),
        Paragraph(f"<b>{tot_e:,.2f}</b>", cell_right)
    ])

    t_sched = Table(sched_data, colWidths=[14*mm, 28*mm, 28*mm, 28*mm, 32*mm, 32*mm, 32*mm])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#ebf5fb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_sched)
    elements.append(Spacer(1, 6))

    # Signatures
    sig_data = [
        [Paragraph("<b>Borrower / Pledgor Signature</b>", cell_center), Paragraph("<b>Appraiser Signature</b>", cell_center), Paragraph("<b>Authorized Signatory / Manager</b>", cell_center)]
    ]
    t_sig = Table(sig_data, colWidths=[63*mm, 63*mm, 68*mm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def create_sb_passbook_excel(sb_data, tx_df):
    """
    Exports a styled Excel (.xlsx) Savings Bank Passbook & Statement:
    - Company & Passbook Header
    - Customer & Account Information Block
    - Summary Metrics Block (Opening Balance, Deposits, Withdrawals, Available Balance)
    - Full Transaction History with Running Balances
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return b""

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SB Passbook"
    ws.views.sheetView[0].showGridLines = True

    # Styles
    navy_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    light_blue_fill = PatternFill(start_color="EBF5FB", end_color="EBF5FB", fill_type="solid")
    soft_gray_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    header_section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    font_title = Font(name="Segoe UI", size=14, bold=True, color="1F4E78")
    font_sub = Font(name="Segoe UI", size=9, color="4B5563")
    font_section = Font(name="Segoe UI", size=11, bold=True, color="1F4E78")
    font_header_white = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Segoe UI", size=10, bold=True, color="111827")
    font_normal = Font(name="Segoe UI", size=9.5, color="111827")

    border_color = "D0D5DD"
    thin_side = Side(style='thin', color=border_color)
    double_bottom_side = Side(style='double', color="1F4E78")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    summary_border = Border(top=thin_side, bottom=double_bottom_side, left=thin_side, right=thin_side)

    # 1. Company Header
    ws.merge_cells("A1:G1")
    ws["A1"] = "AARSHA NIDHI LIMITED"
    ws["A1"].font = font_title
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    ws.merge_cells("A2:G2")
    ws["A2"] = "6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501"
    ws["A2"].font = font_sub
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 14

    ws.merge_cells("A3:G3")
    ws["A3"] = "CIN: U65990KL2021PLN069978 | Ph: 0471-2994535"
    ws["A3"].font = font_sub
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 14

    ws.merge_cells("A4:G4")
    ws["A4"] = "SAVINGS BANK (SB) PASSBOOK & STATEMENT OF ACCOUNT"
    ws["A4"].font = Font(name="Segoe UI", size=12, bold=True, color="FFFFFF")
    ws["A4"].fill = navy_fill
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[4].height = 22

    # 2. Account Details Section
    acc_no = sb_data.get("acc_no", "N/A")
    c_name = sb_data.get("cust_name", "N/A")
    phone = sb_data.get("phone", "N/A")
    created_at = sb_data.get("created_at", "N/A")
    rate = float(sb_data.get("rate", 3.5))
    balance = float(sb_data.get("balance", 0.0))
    addr = f"{sb_data.get('street', '')}, {sb_data.get('city', '')}".strip(" ,") or "Balaramapuram"

    ws["A6"] = "Account Number:"
    ws["B6"] = str(acc_no)
    ws["D6"] = "Customer Name:"
    ws["E6"] = str(c_name)

    ws["A7"] = "Account Type:"
    ws["B7"] = "Savings Bank (SB) Account"
    ws["D7"] = "Phone / Contact:"
    ws["E7"] = str(phone)

    ws["A8"] = "Opening Date:"
    ws["B8"] = str(created_at)
    ws["D8"] = "Interest Rate:"
    ws["E8"] = f"{rate}% p.a."

    ws["A9"] = "Address:"
    ws["B9"] = str(addr)
    ws["D9"] = "Available Balance:"
    ws["E9"] = f"₹{balance:,.2f}"

    for r in range(6, 10):
        for c_idx in [1, 4]:
            cell = ws.cell(row=r, column=c_idx)
            cell.font = font_bold
            cell.fill = light_blue_fill
            cell.border = thin_border
        for c_idx in [2, 3, 5, 6, 7]:
            cell = ws.cell(row=r, column=c_idx)
            cell.font = font_normal
            cell.border = thin_border

    # 3. Summary Metrics
    op_bal = float(sb_data.get("opening_balance", 0.0))
    tot_dep = float(sb_data.get("total_deposits", 0.0))
    tot_wdr = float(sb_data.get("total_withdrawals", 0.0))

    ws["A11"] = "Opening Balance"
    ws["B11"] = f"₹{op_bal:,.2f}"
    ws["C11"] = "Total Deposits"
    ws["D11"] = f"₹{tot_dep:,.2f}"
    ws["E11"] = "Total Withdrawals"
    ws["F11"] = f"₹{tot_wdr:,.2f}"
    ws["G11"] = f"₹{balance:,.2f}"

    for c in range(1, 8):
        cell = ws.cell(row=11, column=c)
        cell.font = font_bold
        cell.fill = header_section_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 4. Transactions Table Header
    headers = ["Date", "Tx ID / Ref", "Particulars / Narration", "Payment Mode", "Debit / Withdrawal (₹)", "Credit / Deposit (₹)", "Running Balance (₹)"]
    row_num = 13
    for col_num, h_text in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col_num, value=h_text)
        cell.font = font_header_white
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[row_num].height = 20

    # 5. Data Rows
    row_num = 14
    if hasattr(tx_df, 'empty') and not tx_df.empty:
        for idx, r in tx_df.iterrows():
            d_val = str(r.get("Date", r.get("date", "")))
            tx_val = str(r.get("Tx ID", r.get("tx_id", "")))
            p_val = str(r.get("Particulars", r.get("narration", "")))
            m_val = str(r.get("Mode", r.get("mode", "CASH")))
            dr_val = float(r.get("Debit", r.get("debit_amount", 0.0)) or 0.0)
            cr_val = float(r.get("Credit", r.get("credit_amount", 0.0)) or 0.0)
            bal_val = float(r.get("Balance", r.get("balance", 0.0)) or 0.0)

            ws.cell(row=row_num, column=1, value=d_val).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=2, value=tx_val).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=3, value=p_val).alignment = Alignment(horizontal="left")
            ws.cell(row=row_num, column=4, value=m_val).alignment = Alignment(horizontal="center")
            
            c_dr = ws.cell(row=row_num, column=5, value=dr_val if dr_val > 0 else "-")
            c_dr.alignment = Alignment(horizontal="right")
            if dr_val > 0: c_dr.number_format = '#,##0.00'

            c_cr = ws.cell(row=row_num, column=6, value=cr_val if cr_val > 0 else "-")
            c_cr.alignment = Alignment(horizontal="right")
            if cr_val > 0: c_cr.number_format = '#,##0.00'

            c_bal = ws.cell(row=row_num, column=7, value=bal_val)
            c_bal.alignment = Alignment(horizontal="right")
            c_bal.number_format = '#,##0.00'

            fill_to_use = soft_gray_fill if (idx % 2 == 1) else None
            for col in range(1, 8):
                cell = ws.cell(row=row_num, column=col)
                cell.font = font_normal
                cell.border = thin_border
                if fill_to_use:
                    cell.fill = fill_to_use

            ws.row_dimensions[row_num].height = 18
            row_num += 1

    # Totals Row
    ws.cell(row=row_num, column=1, value="TOTAL").alignment = Alignment(horizontal="center")
    ws.cell(row=row_num, column=2, value="-").alignment = Alignment(horizontal="center")
    ws.cell(row=row_num, column=3, value="Statement Closing Summary").alignment = Alignment(horizontal="left")
    ws.cell(row=row_num, column=4, value="-").alignment = Alignment(horizontal="center")
    
    t_dr = ws.cell(row=row_num, column=5, value=tot_wdr)
    t_dr.number_format = '#,##0.00'
    t_dr.alignment = Alignment(horizontal="right")
    
    t_cr = ws.cell(row=row_num, column=6, value=tot_dep)
    t_cr.number_format = '#,##0.00'
    t_cr.alignment = Alignment(horizontal="right")

    t_b = ws.cell(row=row_num, column=7, value=balance)
    t_b.number_format = '#,##0.00'
    t_b.alignment = Alignment(horizontal="right")

    for col in range(1, 8):
        cell = ws.cell(row=row_num, column=col)
        cell.font = font_bold
        cell.fill = light_blue_fill
        cell.border = summary_border

    # Adjust column widths
    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 34
    ws.column_dimensions['D'].width = 16
    ws.column_dimensions['E'].width = 22
    ws.column_dimensions['F'].width = 22
    ws.column_dimensions['G'].width = 22

    from io import BytesIO
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def create_sb_passbook_pdf(sb_data, tx_df):
    """
    Generates an official high-resolution printable Savings Bank Passbook & Statement PDF:
    - Company & Passbook Header
    - Account & Customer Details Card
    - Metrics Summary
    - Transaction History with Running Balances
    - Signatures Footer
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        return b""

    from io import BytesIO
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('SBTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=16, alignment=1, textColor=colors.HexColor('#1f4e78'))
    sub_style = ParagraphStyle('SBSub', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, alignment=1, textColor=colors.HexColor('#4b5563'))
    sec_title = ParagraphStyle('SBSec', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=colors.HexColor('#1f4e78'))
    th_style = ParagraphStyle('SBTH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=1, textColor=colors.white)
    cell_left = ParagraphStyle('SBCellL', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=0)
    cell_center = ParagraphStyle('SBCellC', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=1)
    cell_right = ParagraphStyle('SBCellR', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=2)

    elements = []

    # 1. Company Header
    elements.append(Paragraph("<b>AARSHA NIDHI LIMITED</b>", title_style))
    elements.append(Paragraph("6/614, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", sub_style))
    elements.append(Paragraph("CIN: U65990KL2021PLN069978 | Ph: 0471-2994535", sub_style))
    elements.append(Spacer(1, 4))

    # Banner
    t_banner = Table([[Paragraph("<b>SAVINGS BANK (SB) PASSBOOK & STATEMENT OF ACCOUNT</b>", th_style)]], colWidths=[260 * mm])
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1f4e78')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_banner)
    elements.append(Spacer(1, 4))

    # 2. Account Details Block
    acc_no = sb_data.get("acc_no", "N/A")
    c_name = sb_data.get("cust_name", "N/A")
    phone = sb_data.get("phone", "N/A")
    created_at = sb_data.get("created_at", "N/A")
    rate = float(sb_data.get("rate", 3.5))
    balance = float(sb_data.get("balance", 0.0))
    op_bal = float(sb_data.get("opening_balance", 0.0))
    tot_dep = float(sb_data.get("total_deposits", 0.0))
    tot_wdr = float(sb_data.get("total_withdrawals", 0.0))
    addr = f"{sb_data.get('street', '')}, {sb_data.get('city', '')}".strip(" ,") or "Balaramapuram"

    info_data = [
        [
            Paragraph("<b>Account Number:</b>", cell_left), Paragraph(str(acc_no), cell_left),
            Paragraph("<b>Customer Name:</b>", cell_left), Paragraph(str(c_name), cell_left),
            Paragraph("<b>Interest Rate:</b>", cell_left), Paragraph(f"{rate}% p.a.", cell_left)
        ],
        [
            Paragraph("<b>Account Type:</b>", cell_left), Paragraph("Savings Bank (SB)", cell_left),
            Paragraph("<b>Phone / Mobile:</b>", cell_left), Paragraph(str(phone), cell_left),
            Paragraph("<b>Opening Date:</b>", cell_left), Paragraph(str(created_at), cell_left)
        ],
        [
            Paragraph("<b>Opening Balance:</b>", cell_left), Paragraph(f"₹{op_bal:,.2f}", cell_left),
            Paragraph("<b>Total Deposits:</b>", cell_left), Paragraph(f"₹{tot_dep:,.2f}", cell_left),
            Paragraph("<b>Available Balance:</b>", cell_left), Paragraph(f"<b>₹{balance:,.2f}</b>", cell_left)
        ]
    ]
    t_info = Table(info_data, colWidths=[32*mm, 52*mm, 32*mm, 58*mm, 34*mm, 52*mm])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#ebf5fb')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#ebf5fb')),
        ('BACKGROUND', (4,0), (4,-1), colors.HexColor('#ebf5fb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 5))

    # 3. Transactions Table
    elements.append(Paragraph("<b>TRANSACTION LEDGER & PASSBOOK ENTRIES</b>", sec_title))
    tx_table_data = [[
        Paragraph("Date", th_style),
        Paragraph("Tx Ref", th_style),
        Paragraph("Particulars / Narration", th_style),
        Paragraph("Mode", th_style),
        Paragraph("Debit / Withdrawal (₹)", th_style),
        Paragraph("Credit / Deposit (₹)", th_style),
        Paragraph("Running Balance (₹)", th_style)
    ]]

    if hasattr(tx_df, 'empty') and not tx_df.empty:
        for _, r in tx_df.iterrows():
            d_val = str(r.get("Date", r.get("date", "")))
            tx_val = str(r.get("Tx ID", r.get("tx_id", "")))
            p_val = str(r.get("Particulars", r.get("narration", "")))
            m_val = str(r.get("Mode", r.get("mode", "CASH")))
            dr_val = float(r.get("Debit", r.get("debit_amount", 0.0)) or 0.0)
            cr_val = float(r.get("Credit", r.get("credit_amount", 0.0)) or 0.0)
            bal_val = float(r.get("Balance", r.get("balance", 0.0)) or 0.0)

            tx_table_data.append([
                Paragraph(d_val, cell_center),
                Paragraph(tx_val, cell_center),
                Paragraph(p_val, cell_left),
                Paragraph(m_val, cell_center),
                Paragraph(f"{dr_val:,.2f}" if dr_val > 0 else "-", cell_right),
                Paragraph(f"{cr_val:,.2f}" if cr_val > 0 else "-", cell_right),
                Paragraph(f"{bal_val:,.2f}", cell_right)
            ])

    # Totals
    tx_table_data.append([
        Paragraph("<b>TOTAL</b>", cell_center),
        Paragraph("-", cell_center),
        Paragraph("<b>Closing Balance Summary</b>", cell_left),
        Paragraph("-", cell_center),
        Paragraph(f"<b>{tot_wdr:,.2f}</b>", cell_right),
        Paragraph(f"<b>{tot_dep:,.2f}</b>", cell_right),
        Paragraph(f"<b>{balance:,.2f}</b>", cell_right)
    ])

    t_tx = Table(tx_table_data, colWidths=[24*mm, 28*mm, 82*mm, 26*mm, 32*mm, 32*mm, 36*mm])
    t_tx.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f4e78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d5dd')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#ebf5fb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_tx)
    elements.append(Spacer(1, 8))

    # Signatures
    sig_data = [
        [Paragraph("<b>Customer / Account Holder Signature</b>", cell_center), Paragraph("<b>Cashier / Accountant Signature</b>", cell_center), Paragraph("<b>Authorized Signatory / Branch Manager</b>", cell_center)]
    ]
    t_sig = Table(sig_data, colWidths=[85*mm, 85*mm, 90*mm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()




