import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & CONNECTION ---
st.set_page_config(page_title="ระบบจัดการใบเสนอราคา (Full Version)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"เชื่อมต่อฐานข้อมูลล้มเหลว: {e}")
    st.stop()

# --- 2. ฟังก์ชันจัดการข้อมูล (CRUD) ---
def fetch_customers():
    res = conn.table("customers").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['id', 'name', 'address'])

def fetch_products():
    res = conn.table("products").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['code', 'name', 'unit', 'price'])

# --- 3. ฟังก์ชันสร้าง PDF (คงพิกัด A4 Chrome) ---
def create_pdf(doc_no, c_name, c_addr, df_items, subtotal, vat, grand_total, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path); pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else: use_f = 'Arial'

    # โลโก้
    logo_file = next((f"logo.{ext}" for ext in ['png','jpg','jpeg','PNG','JPG'] if os.path.exists(f"logo.{ext}")), None)
    y_pos = 35 if logo_file else 10
    if logo_file: pdf.image(logo_file, x=10, y=10, w=30)

    # หัวเอกสาร
    pdf.set_y(y_pos); pdf.set_font(use_f, 'B', 22)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R')
    
    # ข้อมูลลูกค้า
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(120, 7, f"ชื่อลูกค้า: {c_name}", 0, 0)
    pdf.set_font(use_f, '', 14)
    pdf.cell(0, 7, f"เลขที่: {doc_no}", 0, 1, 'R')
    pdf.cell(120, 7, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 7, f"ที่อยู่: {c_addr}")
    
    # ตาราง 20 แถว
    pdf.ln(2); pdf.set_fill_color(245, 245, 245); pdf.set_font(use_f, 'B', 12)
    w = [10, 25, 70, 15, 15, 25, 30]
    headers = ["ลำดับ", "รหัสสินค้า", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "รวมเงิน"]
    for i in range(7): pdf.cell(w[i], 7.5, headers[i], 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font(use_f, '', 12)
    for i in range(20):
        if i < len(df_items):
            row = df_items.iloc[i]
            d = [str(i+1), str(row.get('รหัสสินค้า','')), str(row.get('รายการ','')),
                 f"{float(row.get('qty_num',0)):,.0f}" if float(row.get('qty_num',0))>0 else "",
                 str(row.get('หน่วย','')), f"{float(row.get('price_num',0)):,.0f}" if float(row.get('price_num',0))>0 else "",
                 f"{float(row.get('รวมเงิน',0)):,.0f}" if float(row.get('รวมเงิน',0))>0 else ""]
        else: d = [""]*7
        for j in range(7):
            align = 'C' if j in [0,1,3,4] else ('L' if j==2 else 'R')
            pdf.cell(w[j], 7.5, d[j], 1, 0, align)
        pdf.ln()

    # สรุปเงิน
    pdf.ln(2); pdf.set_font(use_f, 'B', 14); lw = sum(w[:-1])
    pdf.cell(lw, 7, "รวมเงิน (Sub Total):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{subtotal:,.0f}", 'B', 1, 'R')
    pdf.cell(lw, 7, "ภาษี (VAT 7%):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{vat:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 16); pdf.set_text_color(200, 0, 0)
    pdf.cell(lw, 9, "ยอดรวมสุทธิ:", 0, 0, 'R'); pdf.cell(w[-1], 9, f"{grand_total:,.0f} THB", 'B', 1, 'R')
    
    # ลายเซ็น 3 ช่อง
    pdf.set_y(-45); pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 11)
    for i in range(3):
        pdf.set_xy(10 + (i*65), pdf.get_y())
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.cell(60, 5, f"( {sigs[i]} )", 0, 1, 'C')
        pdf.set_y(pdf.get_y() - 10)
    return bytes(pdf.output())

# --- 4. MAIN UI ---
st.title("📄 ระบบออกใบเสนอราคา (Full System)")

tab1, tab2, tab3 = st.tabs(["📝 ออกใบเสนอราคา", "👥 เพิ่มลูกค้าใหม่", "📦 เพิ่มสินค้าใหม่"])

# --- TAB 1: ออกใบเสนอราคา (ฟังก์ชันหลัก) ---
with tab1:
    df_customers = fetch_customers()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("ส่วนที่ 1: ข้อมูลลูกค้า")
        sid = st.selectbox("เลือกรหัสลูกค้า (จากฐานข้อมูล)", options=["-- เลือก --"] + df_customers['id'].astype(str).tolist())
        target = df_customers[df_customers['id'].astype(str) == sid].iloc[0] if sid != "-- เลือก --" else {}
        c_name = st.text_input("ชื่อลูกค้า", value=target.get('name', ''))
        c_addr = st.text_area("ที่อยู่", value=target.get('address', ''), height=100)
    with col2:
        st.subheader("ส่วนที่ 2: ข้อมูลผู้ลงนาม")
        s1 = st.text_input("ชื่อผู้อนุมัติ (ลูกค้า)", "")
        s2 = st.text_input("ชื่อพนักงานขาย", "")
        s3 = st.text_input("ชื่อผู้จัดการ", "")
        dno = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        v_on = st.checkbox("คิดภาษี VAT 7%", value=True)

    st.divider()
    st.subheader("ส่วนที่ 3: รายการสินค้า")
    grid = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20, num_rows="dynamic", use_container_width=True)
    
    # Logic การคำนวณ
    df_grid = pd.DataFrame(grid)
    df_grid['qty_num'] = pd.to_numeric(df_grid['จำนวน'], errors='coerce').fillna(0)
    df_grid['price_num'] = pd.to_numeric(df_grid['ราคา'], errors='coerce').fillna(0)
    df_grid['รวมเงิน'] = df_grid['qty_num'] * df_grid['price_num']
    
    sub = int(df_grid['รวมเงิน'].sum())
    v_amt = int(sub * 0.07) if v_on else 0
    grand = sub + v_amt

    # --- ปุ่มสร้างใบเสนอราคา ---
    if c_name:
        pdf_bytes = create_pdf(dno, c_name, c_addr, df_grid, sub, v_amt, grand, [s1, s2, s3])
        st.download_button("📥 สร้างใบเสนอราคา (ดาวน์โหลด PDF)", data=pdf_bytes, file_name=f"{dno}.pdf", use_container_width=True, type="primary")

# --- TAB 2: เพิ่มรายชื่อลูกค้าใหม่ ---
with tab2:
    st.subheader("➕ เพิ่มรายชื่อลูกค้าใหม่ลงฐานข้อมูล")
    with st.form("cust_form", clear_on_submit=True):
        ni = st.text_input("รหัสลูกค้า (ID)")
        nn = st.text_input("ชื่อบริษัท / ชื่อลูกค้า")
        na = st.text_area("ที่อยู่")
        if st.form_submit_button("บันทึกข้อมูลลูกค้า"):
            if ni and nn:
                conn.table("customers").insert({"id": ni, "name": nn, "address": na}).execute()
                st.success(f"บันทึกข้อมูล '{nn}' เรียบร้อยแล้ว!")
                st.cache_data.clear() # เคลียร์แคชเพื่อให้ข้อมูลใหม่เด้งไปหน้าออกบิล

# --- TAB 3: เพิ่มสินค้าใหม่ ---
with tab3:
    st.subheader("📦 เพิ่มสินค้าใหม่ลงฐานข้อมูล")
    with st.form("prod_form", clear_on_submit=True):
        pc = st.text_input("รหัสสินค้า")
        pn = st.text_input("ชื่อรายการสินค้า")
        pu = st.text_input("หน่วย")
        pp = st.number_input("ราคาต่อหน่วย", min_value=0)
        if st.form_submit_button("บันทึกข้อมูลสินค้า"):
            if pc and pn:
                conn.table("products").insert({"code": pc, "name": pn, "unit": pu, "price": pp}).execute()
                st.success(f"บันทึกสินค้า '{pn}' เรียบร้อยแล้ว!")
                st.cache_data.clear()
