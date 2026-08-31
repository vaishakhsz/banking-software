import io
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import A5, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from database import IST, get_account_name

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
    elements.append(Paragraph("6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", subheader_style))
    elements.append(Paragraph("CIN: U65990KL22021PLN069978 | Ph: 0471-2994535", subheader_style))
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
    writer.writerow(["6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501"])
    writer.writerow(["CIN: U65990KL22021PLN069978 | Ph: 0471-2994535"])
    
    # 2. Report Title & Date Scope
    date_str = f"From: {from_date} To: {to_date}" if from_date and to_date else ""
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
                    cleaned_row.append("" if val is None else str(val))
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
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

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
    c2.value = "6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501"
    c2.font = Font(name="Segoe UI", size=9, color="4B5563")
    c2.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 16

    # Row 3: CIN
    ws.merge_cells(f"A3:{last_col_letter}3")
    c3 = ws["A3"]
    c3.value = "CIN: U65990KL22021PLN069978 | Ph: 0471-2994535"
    c3.font = Font(name="Segoe UI", size=9, color="4B5563")
    c3.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 16

    # Row 4: Title & Date Range
    ws.merge_cells(f"A4:{last_col_letter}4")
    c4 = ws["A4"]
    date_str = f" (From: {from_date} To: {to_date})" if from_date and to_date else ""
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
                    cell.value = str(val) if val is not None else ""
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
    elements.append(Paragraph("6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", sub_header_style))
    elements.append(Paragraph("CIN: U65990KL22021PLN069978 | Ph: 0471-2994535", sub_header_style))
    elements.append(Spacer(1, 4))
    
    if voucher_type == 'CB':
        date_val, v_num, part, dr, cr, acc_code, narr = voucher_data[0]
        acc_name = get_account_name(acc_code)
        account_display = f"{acc_code} - {acc_name}" if acc_name else acc_code
        
        elements.append(Paragraph("CASH VOUCHER (CB)", title_style))
        elements.append(Spacer(1, 4))
        
        voucher_content = [
            ["Voucher No:", v_num, "Date:", date_val],
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
            ["Voucher No:", v_num, "Date:", date_val],
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
             Paragraph(f"<b>Date:</b> {jv_date}", normal_style)]
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
    
    fd_id, c_name, street, city, state, pincode, principal, tenure, rate, maturity, nominee, created_at, status, closed_date = fd_data
    full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
    status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"
    
    elements.append(Paragraph("AARSHA NIDHI LIMITED", title_style))
    elements.append(Paragraph("6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", subtitle_style))
    elements.append(Paragraph("CIN: U65990KL22021PLN069978 | Ph: 0471-2994535", subtitle_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("FIXED DEPOSIT RECEIPT / LEDGER", heading_style))
    
    status_color = colors.red if status == 'CLOSED' else colors.green
    elements.append(Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", status_style))
    
    detail_data = [
        [Paragraph("<b>FDR No. / A/c No:</b>", detail_label), Paragraph(f"FD-{fd_id:05d}", detail_value),
         Paragraph("<b>A/c Opening Date:</b>", detail_label), Paragraph(created_at, detail_value)],
        [Paragraph("<b>Name:</b>", detail_label), Paragraph(c_name, detail_value),
         Paragraph("<b>Interest Rate:</b>", detail_label), Paragraph(f"{rate}% p.a.", detail_value)],
        [Paragraph("<b>Address:</b>", detail_label), Paragraph(full_address, detail_value),
         Paragraph("<b>Status:</b>", detail_label), Paragraph(status_text, detail_value)],
        [Paragraph("<b>Mode of Op.:</b>", detail_label), Paragraph("Single", detail_value),
         Paragraph("<b>Nominee:</b>", detail_label), Paragraph(nominee if nominee else 'N/A', detail_value)],
        [Paragraph("<b>Period / Tenure:</b>", detail_label), Paragraph(f"{tenure} MONTHS", detail_value),
         Paragraph("<b>Maturity Amount:</b>", detail_label), Paragraph(f"₹{maturity:,.2f}", detail_value)],
    ]
    if status == 'CLOSED':
        detail_data.append([Paragraph("<b>Closed Date:</b>", detail_label), Paragraph(closed_date, detail_value), "", ""])
    
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
        Paragraph(created_at, table_cell_center),
        Paragraph("Opening Balance / Principal Deposit", table_cell_left),
        Paragraph("-", table_cell_center),
        Paragraph(f"₹{principal:,.2f}", table_cell_right),
        Paragraph(f"₹{principal:,.2f}", table_cell_right),
        Paragraph("0", table_cell_center),
        Paragraph("0", table_cell_center)
    ])
    
    if status == 'CLOSED':
        ledger_data.append([
            Paragraph(closed_date, table_cell_center),
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
        elements.append(Paragraph("⚠️ This Fixed Deposit has been CLOSED", warning_style))
    
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
    
    rd_id, c_name, street, city, state, pincode, monthly_amt, tenure, rate, paid_inst, maturity, nominee, created_at, status, closed_date = rd_data
    full_address = f"{street}, {city}, {state} - {pincode}" if street else f"{city}, {state} - {pincode}"
    total_deposited = monthly_amt * paid_inst
    status_text = "CLOSED" if status == 'CLOSED' else "ACTIVE"
    
    elements.append(Paragraph("AARSHA NIDHI LIMITED", title_style))
    elements.append(Paragraph("6/814, ARS Complex, Kattakada Road, Balaramapuram P.O, Thiruvananthapuram - 695501", subtitle_style))
    elements.append(Paragraph("CIN: U65990KL22021PLN069978 | Ph: 0471-2994535", subtitle_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("RECURRING DEPOSIT RECEIPT / LEDGER", heading_style))
    
    status_color = colors.red if status == 'CLOSED' else colors.blue
    elements.append(Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", status_style))
    
    detail_data = [
        [Paragraph("<b>RDR No. / A/c No:</b>", detail_label), Paragraph(f"RD-{rd_id:05d}", detail_value),
         Paragraph("<b>A/c Opening Date:</b>", detail_label), Paragraph(created_at, detail_value)],
        [Paragraph("<b>Name:</b>", detail_label), Paragraph(c_name, detail_value),
         Paragraph("<b>Interest Rate:</b>", detail_label), Paragraph(f"{rate}% p.a.", detail_value)],
        [Paragraph("<b>Address:</b>", detail_label), Paragraph(full_address, detail_value),
         Paragraph("<b>Status:</b>", detail_label), Paragraph(status_text, detail_value)],
        [Paragraph("<b>Monthly Installment:</b>", detail_label), Paragraph(f"₹{monthly_amt:,.2f}", detail_value),
         Paragraph("<b>Nominee:</b>", detail_label), Paragraph(nominee if nominee else 'N/A', detail_value)],
        [Paragraph("<b>Tenure:</b>", detail_label), Paragraph(f"{tenure} MONTHS", detail_value),
         Paragraph("<b>Installments Paid:</b>", detail_label), Paragraph(f"{paid_inst} / {tenure}", detail_value)],
    ]
    if status == 'CLOSED':
        detail_data.append([Paragraph("<b>Closed Date:</b>", detail_label), Paragraph(closed_date, detail_value), "", ""])
    
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
    elements.append(Paragraph(f"<b>Deposit Repayable:</b> Recurring Deposit of <b>₹{monthly_amt:,.2f}</b> monthly for {tenure} months. Estimated Maturity Amount: <b>₹{maturity:,.2f}</b>.", box_style))
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
        Paragraph(created_at, table_cell_center),
        Paragraph("RD Account Opening & Installment 1", table_cell_left),
        Paragraph("-", table_cell_center),
        Paragraph(f"₹{monthly_amt:,.2f}", table_cell_right),
        Paragraph(f"₹{total_deposited:,.2f}", table_cell_right),
        Paragraph(str(paid_inst), table_cell_center)
    ])
    
    if status == 'CLOSED':
        ledger_data.append([
            Paragraph(closed_date, table_cell_center),
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
        elements.append(Paragraph("⚠️ This Recurring Deposit has been CLOSED", warning_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
