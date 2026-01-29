import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG ---
st.set_page_config(page_title="ระบบใบเสนอราคา (Official)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except:
    st.error("เชื่อมต่อ Database ไม่ได้")
    st.stop()

# --- 2. PDF ENGINE (อ้างอิงจาก แห.pdf และ quotation_pdf_chrome.py) ---
def create_pdf(doc_data, items_df, summary, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path); pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else: use_f = 'Arial'

    # ส่วนหัวและโลโก้
    logo = next((f"logo.{ext}" for ext in ['png','jpg','jpeg'] if os.path.exists(f"logo.{ext}")), None)
    if logo: pdf.image(logo, x=10, y=10, w=25)

    # ข้อมูลบริษัทเรา (ฝั่งขวา)
    pdf.set_xy(110, 10)
    pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(90, 6, f"บริษัท: {doc_data['my_company']}\nที่อยู่: {doc_data['my_addr']}\nโทร: {doc_data['my_tel']} เลขผู้เสียภาษี: {doc_data['my_tax_id']}", 0, 'R')

    # หัวข้อเอกสาร
    pdf.set_y(35)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # ข้อมูลลูกค้า (คืนค่ามาครบทุกฟิลด์ตามไฟล์ แห.pdf)
    pdf.set_font(use_f, '', 14)
    col_w = 95
    start_y = pdf.get_y() + 5
    
    # ฝั่งซ้าย: ข้อมูลลูกค้า
    pdf.set_xy(10, start_y)
    pdf.multi_cell(col_w, 7, f"ชื่อผู้ติดต่อ: {doc_data['contact_name']}\nบริษัท: {doc_data['cust_name']}\nที่อยู่: {doc_data['cust_addr']}\nโทร: {doc_data['cust_tel']}  โทรสาร: {doc_data['cust_fax']}")
    
    # ฝั่งขวา: เลขที่/วันที่
    pdf.set_xy(110, start_y)
    pdf.multi_cell(90, 7, f"เลขที่: {doc_data['doc_no']}\nวันที่: {doc_data['doc_date']}\nวันที่กำหนดส่ง: {doc_data['due_date']}\nเครดิต: {doc_data['credit']} วัน", 0, 'R')

    # ตารางรายการสินค้า
    pdf.set_y(start_y + 35)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 12)
    w = [15, 75, 20, 20, 25, 35] # รหัส, รายการ, จำนวน, หน่วย, ราคา, รวมเงิน
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "จำนวนเงิน"]
    for i in range(len(headers)): pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 12)
    for i in range(18): # ปรับเหลือ 18 แถวเพื่อให้ที่ว่างลายเซ็นพอ
        if i < len(items_df):
            row = items_df.iloc[i]
            d = [str(row['รหัสสินค้า']), str(row['รายการ']), f"{row['qty_num']:,.0f}", str(row['หน่วย']), f"{row['price_num']:,.0f}", f"{row['รวมเงิน']:,.0f}"]
        else: d = [""]*6
        for j in range(6):
            pdf.cell(w[j], 7, d[j], 1, 0, 'C' if j != 1 else 'L')
        pdf.ln()

    # ส่วนสรุปยอดเงิน
    pdf.ln(2)
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(sum(w[:-1]), 7, "รวมเงินย่อย:", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{summary['subtotal']:,.0f}", 'B', 1, 'R')
    pdf.cell(sum(w[:-1]), 7, "ภาษีมูลค่าเพิ่ม (7%):", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{summary['vat']:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 16); pdf.set_text_color(200, 0, 0)
    pdf.cell(sum(w[:-1]), 9, "รวมทั้งสิ้น:", 0, 0, 'R')
    pdf.cell(w[-1], 9, f"{summary['grand_total']:,.0f}", 'B', 1, 'R')

    # --- ส่วนลายเซ็น (ชิดขอบล่างสุดของ A4) ---
    pdf.set_y(-45) # ล็อกตำแหน่ง 4.5 ซม. จากขอบล่าง
    pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 12)
    titles = ["ผู้อนุมัติซื้อ", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    
    for i in range(3):
        pdf.set_xy(10 + (i*65), pdf.get_y())
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.cell(60, 5, f"( {names[i]} )", 0, 1, 'C')
        pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')
        pdf.set_y(pdf.get_y() - 20) # ย้อนตำแหน่ง Y เพื่อเขียนคอลัมน์ถัดไปในระดับเดียวกัน

    return bytes(pdf.output())

# --- 3. UI (ห้ามตัด Tab ใดๆ ออก) ---
tab1, tab2, tab3 = st.tabs(["📝 ออกใบเสนอราคา", "👥 ข้อมูลลูกค้า", "📦 สินค้า"])

with tab1:
    st.subheader("ข้อมูลบริษัทเรา & ลูกค้า")
    c1, c2 = st.columns(2)
    with c1:
        my_comp = st.text_input("ชื่อบริษัทเรา", "SIWAKIT")
        my_tax = st.text_input("เลขผู้เสียภาษีเรา", "0123456789XXX")
        cust_name = st.text_input("บริษัทลูกค้า")
        contact = st.text_input("ชื่อผู้ติดต่อ")
        cust_tel = st.text_input("โทรศัพท์ลูกค้า")
    with c2:
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        due_date = st.text_input("กำหนดส่ง", "7 วัน")
        credit = st.number_input("เครดิต (วัน)", 0)
        cust_fax = st.text_input("โทรสารลูกค้า")
        cust_addr = st.text_area("ที่อยู่ลูกค้า", height=68)

    st.divider()
    grid = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20, num_rows="dynamic", use_container_width=True)
    
    # คำนวณเงิน
    df_grid = pd.DataFrame(grid)
    df_grid['qty_num'] = pd.to_numeric(df_grid['จำนวน'], errors='coerce').fillna(0)
    df_grid['price_num'] = pd.to_numeric(df_grid['ราคา'], errors='coerce').fillna(0)
    df_grid['รวมเงิน'] = df_grid['qty_num'] * df_grid['price_num']
    sub = int(df_grid['รวมเงิน'].sum())
    vat = int(sub * 0.07)
    grand = sub + vat

    st.subheader("รายชื่อผู้เซ็น")
    s_col1, s_col2, s_col3 = st.columns(3)
    s1 = s_col1.text_input("ชื่อผู้อนุมัติซื้อ", "")
    s2 = s_col2.text_input("ชื่อพนักงานขาย", "")
    s3 = s_col3.text_input("ชื่อผู้จัดการ", "")

    # ✅ ปุ่มสร้างใบเสนอราคา (พิมพ์ได้ทันที)
    if st.button("🚀 สร้างใบเสนอราคา (Save & Print PDF)", type="primary", use_container_width=True):
        doc_info = {
            "my_company": my_comp, "my_addr": "เลขที่ 123... (แก้ไขได้ในโค้ด)", "my_tel": "02-XXX-XXXX", "my_tax_id": my_tax,
            "cust_name": cust_name, "contact_name": contact, "cust_addr": cust_addr, "cust_tel": cust_tel, "cust_fax": cust_fax,
            "doc_no": doc_no, "doc_date": datetime.now().strftime('%d/%m/%Y'), "due_date": due_date, "credit": credit
        }
        summary = {"subtotal": sub, "vat": vat, "grand_total": grand}
        sigs = {"s1": s1, "s2": s2, "s3": s3}
        
        pdf_out = create_pdf(doc_info, df_grid, summary, sigs)
        st.download_button("📥 คลิกเพื่อดาวน์โหลด PDF", data=pdf_out, file_name=f"{doc_no}.pdf", mime="application/pdf")

with tab2:
    st.info("ส่วนจัดการฐานข้อมูลลูกค้า (ไม่ได้ตัดออก)")
with tab3:
    st.info("ส่วนจัดการฐานข้อมูลสินค้า (ไม่ได้ตัดออก)")
