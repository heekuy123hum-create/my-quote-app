import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & DB ---
st.set_page_config(page_title="ระบบใบเสนอราคา (Official)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except:
    st.error("เชื่อมต่อ Database ไม่ได้")
    st.stop()

def get_logo():
    for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG']:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 2. PDF ENGINE (ถอดแบบจาก quotation_pdf_chrome) ---
def create_pdf(doc_no, c_name, c_addr, df_items, subtotal, vat, grand_total, sig_names):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # --- ส่วนหัว (Header) ---
    logo = get_logo()
    content_y = 10
    if logo:
        pdf.image(logo, x=10, y=10, w=30)
        content_y = 35 # เริ่มเนื้อหาใต้โลโก้พอดี ไม่ทับกันแน่นอน

    pdf.set_y(content_y)
    pdf.set_font(use_f, 'B', 22)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R')

    # --- ข้อมูลลูกค้า (Customer) ---
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(120, 7, "ข้อมูลลูกค้า (Customer Details):", 0, 0)
    pdf.set_font(use_f, '', 14)
    pdf.cell(0, 7, f"เลขที่: {doc_no}", 0, 1, 'R')

    pdf.cell(120, 7, f"ชื่อลูกค้า: {c_name if c_name else ''}", 0, 0)
    pdf.cell(0, 7, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 7, f"ที่อยู่: {c_addr if c_addr else ''}")
    pdf.ln(2)

    # --- ตาราง 7 คอลัมน์ (Table) ---
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font(use_f, 'B', 12)
    h = 7.5 # ความสูงกำลังดีสำหรับ 20 แถวในหน้าเดียว
    w = [10, 25, 70, 15, 15, 25, 30] 
    headers = ["ลำดับ", "รหัสสินค้า", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "รวมเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], h, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 12)
    for i in range(20):
        if i < len(df_items):
            row = df_items.iloc[i]
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

    # --- ส่วนสรุปเงิน (Summary) ---
    pdf.ln(2)
    pdf.set_font(use_f, 'B', 14)
    label_w = sum(w[:-1])
    
    pdf.cell(label_w, 7, "รวมเงิน (Sub Total):", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{subtotal:,.0f}", 'B', 1, 'R')
    
    pdf.cell(label_w, 7, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{vat:,.0f}", 'B', 1, 'R')
    
    pdf.set_font(use_f, 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(label_w, 8, "ยอดรวมทั้งสิ้น:", 0, 0, 'R')
    pdf.cell(w[-1], 8, f"{grand_total:,.0f} THB", 'B', 1, 'R')
    pdf.set_text_color(0, 0, 0)

    # --- ส่วนลายเซ็น 3 ช่อง (ดึงชื่อจากตัวแปรมาใส่) ---
    # ล็อกตำแหน่งไว้ท้ายกระดาษ (ประมาณ 45mm จากขอบล่าง)
    pdf.set_y(-45)
    pdf.set_font(use_f, '', 12)
    titles = ["ผู้อนุมัติสั่งซื้อ", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    
    for i in range(3):
        pdf.set_xy(10 + (i * 65), pdf.get_y())
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_x(10 + (i * 65))
        pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.set_x(10 + (i * 65))
        # ✅ ใส่ชื่อคนที่กรอกจากหน้าแอป (sig_names)
        pdf.cell(60, 5, f"( {sig_names[i]} )", 0, 1, 'C')
        pdf.set_y(pdf.get_y() - 15) # กลับไประนาบเดิมเพื่อพิมพ์ช่องถัดไป

    return bytes(pdf.output())

# --- 3. UI (อิงตามฟิลด์ในต้นฉบับพี่) ---
st.title("📄 ระบบใบเสนอราคา (Full Version)")

tab1, _, _ = st.tabs(["📝 ออกเอกสาร", "👥 ลูกค้า", "📦 สินค้า"])

with tab1:
    res_c = conn.table("customers").select("*").execute()
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("ข้อมูลลูกค้า")
        sid = st.selectbox("รหัสลูกค้า", options=["-- เลือก --"] + (df_c.iloc[:, 0].tolist() if not df_c.empty else []))
        info = df_c[df_c.iloc[:, 0] == sid].iloc[0] if sid != "-- เลือก --" else {}
        name = st.text_input("ชื่อลูกค้า", value=info.get('name', ''))
        addr = st.text_area("ที่อยู่", value=info.get('address', ''), height=80)
    with c2:
        st.subheader("พนักงานและผู้อนุมัติ")
        s1 = st.text_input("ชื่อผู้อนุมัติ (ลูกค้า)", "")
        s2 = st.text_input("ชื่อพนักงานขาย", "")
        s3 = st.text_input("ชื่อผู้จัดการ", "")
        dno = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        v_on = st.checkbox("คิด VAT 7%", value=True)

    st.divider()
    grid = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20, 
                          num_rows="dynamic", use_container_width=True)
    
    df_grid = pd.DataFrame(grid)
    df_grid['qty_num'] = pd.to_numeric(df_grid['จำนวน'], errors='coerce').fillna(0)
    df_grid['price_num'] = pd.to_numeric(df_grid['ราคา'], errors='coerce').fillna(0)
    df_grid['รวมเงิน'] = df_grid['qty_num'] * df_grid['price_num']
    
    sub = int(df_grid['รวมเงิน'].sum())
    v_amt = int(sub * 0.07) if v_on else 0
    grand = sub + v_amt

    if st.button("✅ บันทึกและดาวน์โหลด PDF (เป๊ะทุกจุด)", type="primary"):
        pdf_out = create_pdf(dno, name, addr, df_grid, sub, v_amt, grand, [s1, s2, s3])
        st.download_button("📥 โหลดไฟล์ PDF", data=pdf_out, file_name=f"{dno}.pdf", mime="application/pdf")
