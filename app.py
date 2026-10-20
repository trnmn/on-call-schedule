import os
import datetime
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def get_first_friday(year):
    """Finds the first on-call Friday of any given calendar year."""
    start_date = datetime.date(year, 1, 1)
    while start_date.weekday() != 4:  # 4 represents Friday
        start_date += datetime.timedelta(days=1)
    return start_date

def get_on_call_weeks(year):
    """Calculates all Friday-to-Thursday shift pairs for a chosen target year."""
    start_date = get_first_friday(year)
    shifts = []
    current_start = start_date
    while current_start.year == year or (current_start + datetime.timedelta(days=6)).year == year:
        current_end = current_start + datetime.timedelta(days=6)
        shifts.append((current_start, current_end))
        current_start += datetime.timedelta(days=7)
    return shifts

def generate_pdf_from_excel(excel_file):
    try:
        df = pd.read_excel(excel_file)
        df.columns = df.columns.str.strip()
        col_mapping = {col.lower(): col for col in df.columns}
        
        year_col = col_mapping.get("target_year")
        anchor_col = col_mapping.get("anchor_year")
        
        year = int(df[year_col].iloc[0]) if year_col and not pd.isna(df[year_col].iloc[0]) else 2027
        anchor_year = int(df[anchor_col].iloc[0]) if anchor_col and not pd.isna(df[anchor_col].iloc[0]) else 2026
            
        ridgeland_col = col_mapping.get("ridgeland_roster")
        hattiesburg_col = col_mapping.get("hattiesburg_roster")
        north_col = col_mapping.get("north_roster")
        
        ridgeland_pool = df[ridgeland_col].dropna().astype(str).str.strip().tolist()
        hattiesburg_pool = df[hattiesburg_col].dropna().astype(str).str.strip().tolist()
        north_pool = df[north_col].dropna().astype(str).str.strip().tolist() if north_col else ["MIKE", "ROBERT"]
            
    except Exception as e:
        year, anchor_year = 2027, 2026
        ridgeland_pool = ["JJONES", "JBOOTH", "WILLIE", "MATT", "BUDDY"]
        hattiesburg_pool = ["TONY", "SCOTT", "JEFFREY", "TIM", "CHASE"]
        north_pool = ["MIKE", "ROBERT"]

    anchor_start = get_first_friday(anchor_year)
    target_start = get_first_friday(year)
    
    elapsed_days = (target_start - anchor_start).days
    week_offset = max(0, elapsed_days // 7)

    weeks = get_on_call_weeks(year)
    months_data = {m: {'name': datetime.date(year, m, 1).strftime('%B').upper(), 'shifts': [], 'north_blocks': []} for m in range(1, 13)}
    
    for idx, (start, end) in enumerate(weeks):
        month_bucket = start.month
        date_str = f"{start.month}/{start.day}–{end.month}/{end.day}"
        if end.year != year: date_str += f"/{str(end.year)[2:]}"
            
        current_global_week = idx + week_offset
        
        ridgeland_person = ridgeland_pool[current_global_week % len(ridgeland_pool)]
        hattiesburg_person = hattiesburg_pool[current_global_week % len(hattiesburg_pool)]
        months_data[month_bucket]['shifts'].append((date_str, f"{ridgeland_person}/{hattiesburg_person}"))

    north_offset = week_offset // 2
    north_idx = north_offset
    i = 0
    while i < len(weeks):
        start_1, end_1 = weeks[i]
        personnel = north_pool[north_idx % len(north_pool)]
        
        if i + 1 < len(weeks):
            start_2, end_2 = weeks[i+1]
            date_str = f"{start_1.month}/{start_1.day}–{end_2.month}/{end_2.day}"
            if end_2.year != year: 
                date_str += f"/{str(end_2.year)[2:]}"
            
            target_month = end_2.month if start_1.month != end_2.month else start_1.month
            months_data[target_month]['north_blocks'].append((date_str, personnel))
            i += 2
            north_idx += 1
            continue
            
        date_str = f"{start_1.month}/{start_1.day}–{end_1.month}/{end_1.day}"
        if end_1.year != year: date_str += f"/{str(end_1.year)[2:]}"
        months_data[start_1.month]['north_blocks'].append((date_str, personnel))
        i += 1
        north_idx += 1

    os.makedirs("generated", exist_ok=True)
    pdf_path = f"generated/Terry_Service_{year}_On_Call_Schedule.pdf"
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=26, leftMargin=26, topMargin=25, bottomMargin=25)
    title_style = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=13, leading=15, alignment=1)
    company_style = ParagraphStyle('CompTitle', fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=1)
    month_header_style = ParagraphStyle('MonthHead', fontName='Helvetica-Bold', fontSize=9, leading=11)
    cell_text = ParagraphStyle('CellText', fontName='Helvetica', fontSize=6.5, leading=8.5)
    cell_text_bold = ParagraphStyle('CellBold', fontName='Helvetica-Bold', fontSize=6.5, leading=8.5)
    footnote_style = ParagraphStyle('Footnote', fontName='Helvetica-Bold', fontSize=7.5, leading=10, alignment=1)

    elements = [
        Paragraph("ON CALL SCHEDULE", title_style),
        Paragraph(f"{year}", title_style),
        Paragraph("TERRY SERVICE, INC.", company_style),
        Spacer(1, 15)
    ]

    def build_month_table(month_dict):
        data = [[Paragraph(month_dict['name'], month_header_style), '']]
        for date, name in month_dict['shifts']:
            data.append([Paragraph(date, cell_text_bold), Paragraph(name, cell_text)])
        data.append([Paragraph("NORTH", cell_text_bold), ''])
        for date, name in month_dict['north_blocks']:
            data.append([Paragraph(date, cell_text_bold), Paragraph(name, cell_text)])
            
        t = Table(data, colWidths=[68, 110])
        t.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,0), 1.2, colors.black),
            ('SPAN', (0,0), (1,0)),
            ('TOPPADDING', (0,0), (-1,-1), 0.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0.5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        return t

    col1_content, col2_content, col3_content = [], [], []
    for m in range(1, 5):
        col1_content.append(build_month_table(months_data[m]))
        col1_content.append(Spacer(1, 10))
    for m in range(5, 9):
        col2_content.append(build_month_table(months_data[m]))
        col2_content.append(Spacer(1, 10))
    for m in range(9, 13):
        col3_content.append(build_month_table(months_data[m]))
        col3_content.append(Spacer(1, 10))

    master_table = Table([[col1_content, '', col2_content, '', col3_content]], colWidths=[178, 13, 178, 13, 178])
    master_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)
    ]))
    
    elements.append(master_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("**FOR ASSISTANCE ON TRACER RELATED SERVICE CALLS PLEASE CALL MARK EASTERLING", footnote_style))

    doc.build(elements)
    return pdf_path

st.title("Terry Service On-Call Schedule Generator")
st.write("Upload your Excel configuration file below to generate the custom annual schedule PDF.")

uploaded_file = st.file_uploader("Upload on_call_config.xlsx", type=["xlsx"])

if uploaded_file is not None:
    with open("temp_config.xlsx", "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    if st.button("Generate Schedule PDF"):
        pdf_path = generate_pdf_from_excel("temp_config.xlsx")
        st.success("Schedule generated successfully!")
        
        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                label="Download PDF Schedule",
                data=pdf_file,
                file_name="On_Call_Schedule.pdf",
                mime="application/pdf"
            )
