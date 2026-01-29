import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. การเชื่อมต่อฐานข้อมูล ---
st.set_page_config(page_title="ระบบออกใบเสนอราคา (Official)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่าความปลอดภัยในระบบให้เรียบร้อยก่อน")
    st.stop()

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"เชื่อมต่อฐานข้อมูลล้มเหลว: {e}")
    st.stop()

# --- 2. ฟังก์ชันค้นหาโลโก้อัตโนมัติ (GitHub) ---
def find_logo():
    for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG']:
        if os.path.exists(f"logo.{ext}"):
            return f"logo.{ext}"
    return None

# --- 3. ฟังก์ชันสร้าง PDF (ดีไซน์ตามไฟล์ที่พี่ส่งมา) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total, sigs):
    pdf = FPDF()
    pdf.add_page()
    
    # ฟอนต์ไทยที่พี่อัปโหลด
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_font = 'THSarabun'
    else:
        pdf.set_font("Arial", '', 14)
        use_font = 'Arial'

    # --- โลโก้มุมซ้ายบน ---
    logo_file = find_logo()
    if logo_file:
        pdf.image(logo_file, x=10, y=10, w=35)
        pdf.set_y(35) 
    else:
        pdf.set_y(20)

    # หัวเอกสาร (ชิดขวาตามไฟล์ต้นฉบับ)
    pdf.set_font(use_font, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R')
    pdf.ln(5)

    # ข้อมูลลูกค้า
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(120, 8, "ข้อมูลลูกค้า (Customer Details):", 0, 0)
    pdf.cell(70, 8, f"เลขที่: {doc_no}", 0, 1, 'R')

    pdf.set_font(use_font, '', 14)
    pdf.cell(120, 8, f"ชื่อลูกค้า: {cust_name if cust_name else ''}", 0, 0)
    pdf.cell(70, 8, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 8, f"ที่อยู่: {cust_addr if cust_addr else ''}")
    pdf.ln(5)

    # --- ตารางรายการ (ตีเส้น 20 แถวให้เต็มแผ่น) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_font, 'B', 12)
    h = 9
    # กำหนดความกว้างคอลัมน์ (ตามฟิลด์ใน quotation_ui.py)
    w = [10, 25, 65, 15, 15, 25, 35] 
    headers = ["ลำดับ", "รหัสสินค้า", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "รวมเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], h, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_font, '', 13)
    for i in range(20):
        if i < len(df_items):
            row = df_items.iloc[i]
            # กรองข้อมูล: ถ้าเป็น 0 หรือว่าง ให้เป็นช่องขาว
            d = [
                str(i + 1),
                str(row.get('รหัสสินค้า', '')),
                str(row.get('รายการ', '')),
                f"{float(row.get('จำนวน', 0)):,.0f}" if float(row.get('จำนวน', 0)) > 0 else "",
                str(row.get('หน่วย', '')),
                f"{float(row.get('ราคา', 0)):,.0f}" if float(row.get('ราคา', 0)) > 0 else "",
                f"{float(row.get('รวมเงิน', 0)):,.0f}" if float(row.get('รวมเงิน', 0)) > 0 else ""
            ]
        else:
            d = ["", "", "", "", "", "", ""]

        for j in range(len(d)):
            align = 'C' if j in [0, 1, 3, 4] else ('L' if j == 2 else 'R')
            pdf.cell(w[j], h, d[j], 1, 0, align)
        pdf.ln()

    # สรุปเงิน
    pdf.ln(3)
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(sum(w[:-1]), 8, "รวมเงินสุทธิ (Sub Total):", 0, 0, 'R')
    pdf.cell(w[-1], 8, f"{subtotal:,.0f}", 'B', 1, 'R')
    pdf.cell(sum(w[:-1]), 8, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(w[-1], 8, f"{vat:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_font, 'B', 16)
    pdf.cell(sum(w[:-1]), 10, "ยอดรวมสุทธิ (Grand Total):", 0, 0, 'R')
    pdf.set_text_color(200, 0, 0)
    pdf.cell(w[-1], 10, f"{grand_total:,.0f} THB", 'B', 1, 'R')
    pdf.set_text_color(0, 0, 0)

    # --- ส่วนเซ็นชื่อ 3 ช่อง (ตามไฟล์ PDF Chrome) ---
    pdf.ln(10)
    sig_y = pdf.get_y()
    pdf.set_font(use_font, '', 12)
    labels = ["ผู้อนุมัติสั่งซื้อ", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    for i in range(3):
        pdf.set_xy(10 + (i*65), sig_y)
        pdf.cell(60, 6, "..........................................", 0, 1, 'C')
        pdf.set_x(10 + (i*65))
        pdf.cell(60, 6, labels[i], 0, 1, 'C')
        pdf.set_x(10 + (i*65))
        pdf.cell(60, 6, f"({sigs[i]})", 0, 1, 'C')

    # ✅ แก้ไขจุดตายที่ทำให้เกิด Error: แปลง bytearray เป็น bytes
    return bytes(pdf.output())

# --- 4. STREAMLIT UI ---
st.title("📄 ระบบใบเสนอราคา (Full Design)")

tab1, tab2, tab3 = st.tabs(["📝 สร้างเอกสาร", "👥 จัดการลูกค้า", "📦 สินค้า"])

with tab1:
    # ดึงข้อมูลลูกค้ามาแสดงใน Selectbox
    res_c = conn.table("customers").select("*").execute()
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("ส่วนที่ 1: ข้อมูลลูกค้า")
        c_list = ["-- เลือก --"] + (df_c.iloc[:, 0].tolist() if not df_c.empty else [])
        sid = st.selectbox("รหัสลูกค้า", options=c_list)
        info = df_c[df_c.iloc[:, 0] == sid].iloc[0] if sid != "-- เลือก --" else {}
        name = st.text_input("ชื่อลูกค้า", value=info.get('name', ''))
        addr = st.text_area("ที่อยู่จัดส่ง", value=info.get('address', ''), height=100)

    with col_right:
        st.subheader("ส่วนที่ 2: ตั้งค่าหน้าเซ็นชื่อ")
        s1 = st.text_input("ชื่อผู้อนุมัติ", "....................")
        s2 = st.text_input("ชื่อพนักงานขาย", "....................")
        s3 = st.text_input("ชื่อผู้จัดการ", "....................")
        dno = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        v_on = st.checkbox("คิด VAT 7%", value=True)

    st.divider()
    
    # ตารางกรอกสินค้า (20 แถว)
    grid_init = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20
    edited = st.data_editor(grid_init, num_rows="dynamic", use_container_width=True)
    
    df_grid = pd.DataFrame(edited)
    df_grid['รวมเงิน'] = pd.to_numeric(df_grid['จำนวน'], 0) * pd.to_numeric(df_grid['ราคา'], 0)
    
    sub = int(df_grid['รวมเงิน'].sum())
    v_amt = int(sub * 0.07) if v_on else 0
    grand = sub + v_amt

    if st.button("บันทึกและสร้าง PDF", type="primary"):
        try:
            # เรียกฟังก์ชันที่แก้ Error Bytearray แล้ว
            pdf_data = create_pdf(dno, name, addr, df_grid, sub, v_amt, grand, [s1, s2, s3])
            st.download_button("📥 ดาวน์โหลดใบเสนอราคา", data=pdf_data, file_name=f"{dno}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
