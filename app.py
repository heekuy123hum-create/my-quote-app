import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & DB ---
st.set_page_config(page_title="ระบบใบเสนอราคา (A4 Perfect Fix)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except:
    st.error("กรุณาเช็กการเชื่อมต่อ Database")
    st.stop()

# --- 2. LOGO AUTO-DETECT ---
def get_logo():
    for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG']:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. PDF ENGINE (โครงสร้างแบบไม่ทับกัน) ---
def create_pdf(doc_no, c_name, c_addr, df_items, subtotal, vat, grand_total, sigs):
    # ใช้ขอบ 10mm เท่ากันทุกด้าน
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else:
        pdf.set_font("Arial", '', 14)
        use_f = 'Arial'

    # --- Header ---
    logo = get_logo()
    if logo:
        pdf.image(logo, x=10, y=10, w=30) # ย่อโลโก้ลงนิดนึง
        pdf.set_y(12)
    else:
        pdf.set_y(10)

    pdf.set_font(use_f, 'B', 22) # ลดขนาดหัวข้อลงนิดนึง
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R')
    pdf.ln(2)

    # ข้อมูลลูกค้า
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(120, 6, "ข้อมูลลูกค้า (Customer Details):", 0, 0)
    pdf.cell(0, 6, f"เลขที่: {doc_no}", 0, 1, 'R')

    pdf.set_font(use_f, '', 14)
    pdf.cell(120, 6, f"ชื่อลูกค้า: {c_name if c_name else ''}", 0, 0)
    pdf.cell(0, 6, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 6, f"ที่อยู่: {c_addr if c_addr else ''}")
    pdf.ln(2)

    # --- Table (บีบความสูงแถวเหลือ 7mm) ---
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font(use_f, 'B', 12)
    h = 7.0 # พระเอกของงาน: ลดความสูงเพื่อหนีส่วนลายเซ็น
    w = [10, 25, 70, 15, 15, 25, 30] 
    headers = ["ลำดับ", "รหัสสินค้า", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "รวมเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], h, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 12)
    for i in range(20):
        if i < len(df_items):
            row = df_items.iloc[i]
            # กรองข้อมูล
            d = [
                str(i + 1),
                str(row.get('รหัสสินค้า', '') or ''),
                str(row.get('รายการ', '') or ''),
                f"{float(row.get('qty_num', 0)):,.0f}" if float(row.get('qty_num', 0)) > 0 else "",
                str(row.get('หน่วย', '') or ''),
                f"{float(row.get('price_num', 0)):,.0f}" if float(row.get('price_num', 0)) > 0 else "",
                f"{float(row.get('รวมเงิน', 0)):,.0f}" if float(row.get('รวมเงิน', 0)) > 0 else ""
            ]
        else:
            d = ["", "", "", "", "", "", ""]

        for j in range(len(d)):
            align = 'C' if j in [0, 1, 3, 4] else ('L' if j == 2 else 'R')
            pdf.cell(w[j], h, d[j], 1, 0, align)
        pdf.ln()

    # --- Summary Section (จัดให้กะทัดรัด) ---
    pdf.ln(1)
    pdf.set_font(use_f, 'B', 13)
    sum_w_label = sum(w[:-1])
    
    pdf.cell(sum_w_label, 7, "รวมเงิน (Sub Total):", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{subtotal:,.0f}", 'B', 1, 'R')
    
    pdf.cell(sum_w_label, 7, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{vat:,.0f}", 'B', 1, 'R')
    
    pdf.set_font(use_f, 'B', 15)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(sum_w_label, 8, "ยอดรวมทั้งสิ้น (Grand Total):", 0, 0, 'R')
    pdf.cell(w[-1], 8, f"{grand_total:,.0f} THB", 'B', 1, 'R')
    pdf.set_text_color(0, 0, 0)

    # --- Signature Section (ล็อกไว้ท้ายกระดาษ ไม่ทับแน่นอน) ---
    # ขยับลงไปที่ -45mm จากขอบล่าง
    pdf.set_y(-45)
    pdf.set_font(use_f, '', 11)
    labels = ["ผู้อนุมัติสั่งซื้อ", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    
    start_x = 10
    for i in range(3):
        pdf.set_xy(start_x + (i * 65), pdf.get_y())
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_x(start_x + (i * 65))
        pdf.cell(60, 5, labels[i], 0, 1, 'C')
        pdf.set_x(start_x + (i * 65))
        pdf.cell(60, 5, f"({sigs[i]})", 0, 1, 'C')
        # คืนค่า Y เพื่อพิมพ์ช่องถัดไปในระนาบเดียวกัน
        pdf.set_y(pdf.get_y() - 15)

    return bytes(pdf.output())

# --- 4. STREAMLIT UI ---
st.title("📄 ระบบใบเสนอราคา (Version: No-Overlap)")

# ส่วนกรอกข้อมูลและคำนวณเงินเหมือนเดิม...
# (ย่อโค้ดส่วน UI เพื่อให้พี่เห็นส่วนสำคัญ)
tab1, tab2, tab3 = st.tabs(["📝 สร้างเอกสาร", "👥 ลูกค้า", "📦 สินค้า"])

with tab1:
    res_c = conn.table("customers").select("*").execute()
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
    
    col1, col2 = st.columns(2)
    with col1:
        sid = st.selectbox("เลือกลูกค้า", options=["-- เลือก --"] + (df_c.iloc[:, 0].tolist() if not df_c.empty else []))
        info = df_c[df_c.iloc[:, 0] == sid].iloc[0] if sid != "-- เลือก --" else {}
        name = st.text_input("ชื่อลูกค้า", value=info.get('name', ''))
        addr = st.text_area("ที่อยู่", value=info.get('address', ''), height=80)
    with col2:
        dno = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        v_on = st.checkbox("VAT 7%", value=True)
        s1 = st.text_input("ชื่อผู้อนุมัติ", "....................")
        s2 = st.text_input("ชื่อพนักงานขาย", "....................")
        s3 = st.text_input("ชื่อผู้จัดการ", "....................")

    st.divider()
    grid_init = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20
    edited = st.data_editor(grid_init, num_rows="dynamic", use_container_width=True)
    
    df_grid = pd.DataFrame(edited)
    df_grid['qty_num'] = pd.to_numeric(df_grid['จำนวน'], errors='coerce').fillna(0)
    df_grid['price_num'] = pd.to_numeric(df_grid['ราคา'], errors='coerce').fillna(0)
    df_grid['รวมเงิน'] = df_grid['qty_num'] * df_grid['price_num']
    
    sub = int(df_grid['รวมเงิน'].sum())
    v_amt = int(sub * 0.07) if v_on else 0
    grand = sub + v_amt

    if st.button("✅ สร้าง PDF และแก้ปัญหาการทับกัน", type="primary"):
        pdf_out = create_pdf(dno, name, addr, df_grid, sub, v_amt, grand, [s1, s2, s3])
        st.download_button("📥 ดาวน์โหลดไฟล์", data=pdf_out, file_name=f"{dno}.pdf", mime="application/pdf")
