import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & CONNECTION (ห้ามตัด) ---
st.set_page_config(page_title="ระบบจัดการใบเสนอราคา (Full Version)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    # เชื่อมต่อกับ Supabase
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"การเชื่อมต่อฐานข้อมูลมีปัญหา: {e}")
    st.stop()

# --- 2. DATA FUNCTIONS (ห้ามตัด) ---
def fetch_customers():
    """ดึงข้อมูลลูกค้าทั้งหมดจาก Database"""
    res = conn.table("customers").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['id', 'name', 'address'])

def fetch_products():
    """ดึงข้อมูลสินค้าทั้งหมดจาก Database"""
    res = conn.table("products").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['code', 'name', 'unit', 'price'])

# --- 3. PDF ENGINE (โครงสร้าง A4 เป๊ะตามต้นฉบับ Chrome) ---
def create_pdf(doc_no, c_name, c_addr, df_items, subtotal, vat, grand_total, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # การตั้งค่าฟอนต์ TH Sarabun New
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # จัดการโลโก้ (ถ้ามีไฟล์จะแสดง และขยับเนื้อหาลงมาไม่ให้ทับ)
    logo_file = next((f"logo.{ext}" for ext in ['png','jpg','jpeg','PNG','JPG'] if os.path.exists(f"logo.{ext}")), None)
    y_pos = 35 if logo_file else 10
    if logo_file:
        pdf.image(logo_file, x=10, y=10, w=30)

    # หัวเอกสาร
    pdf.set_y(y_pos)
    pdf.set_font(use_f, 'B', 22)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R')

    # ส่วนข้อมูลลูกค้า
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(120, 7, f"ชื่อลูกค้า: {c_name}", 0, 0)
    pdf.set_font(use_f, '', 14)
    pdf.cell(0, 7, f"เลขที่: {doc_no}", 0, 1, 'R')
    pdf.cell(120, 7, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 7, f"ที่อยู่: {c_addr}")
    
    # ตารางรายการสินค้า 20 แถว
    pdf.ln(2)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font(use_f, 'B', 12)
    h = 7.5 # ความสูงต่อแถวเพื่อให้พอดีหน้า A4
    w = [10, 25, 70, 15, 15, 25, 30]
    headers = ["ลำดับ", "รหัสสินค้า", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "รวมเงิน"]
    for i in range(7):
        pdf.cell(w[i], h, headers[i], 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font(use_f, '', 12)
    for i in range(20):
        if i < len(df_items):
            row = df_items.iloc[i]
            d = [str(i+1), str(row.get('รหัสสินค้า','')), str(row.get('รายการ','')),
                 f"{float(row.get('qty_num',0)):,.0f}" if float(row.get('qty_num',0))>0 else "",
                 str(row.get('หน่วย','')), f"{float(row.get('price_num',0)):,.0f}" if float(row.get('price_num',0))>0 else "",
                 f"{float(row.get('รวมเงิน',0)):,.0f}" if float(row.get('รวมเงิน',0))>0 else ""]
        else:
            d = [""]*7
        for j in range(7):
            align = 'C' if j in [0,1,3,4] else ('L' if j==2 else 'R')
            pdf.cell(w[j], h, d[j], 1, 0, align)
        pdf.ln()

    # ส่วนสรุปยอดเงิน
    pdf.ln(2)
    pdf.set_font(use_f, 'B', 14)
    lw = sum(w[:-1])
    pdf.cell(lw, 7, "รวมเงิน (Sub Total):", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{subtotal:,.0f}", 'B', 1, 'R')
    pdf.cell(lw, 7, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(w[-1], 7, f"{vat:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(lw, 9, "ยอดรวมสุทธิ (Grand Total):", 0, 0, 'R')
    pdf.cell(w[-1], 9, f"{grand_total:,.0f} THB", 'B', 1, 'R')
    pdf.set_text_color(0, 0, 0)

    # ส่วนท้าย: ลายเซ็น 3 ตำแหน่ง (ดึงชื่อจากตัวแปร sigs)
    pdf.set_y(-45)
    pdf.set_font(use_f, '', 11)
    titles = ["ผู้อนุมัติสั่งซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    for i in range(3):
        pdf.set_xy(10 + (i*65), pdf.get_y())
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.cell(60, 5, f"{titles[i]}", 0, 1, 'C')
        pdf.cell(60, 5, f"( {sigs[i]} )", 0, 1, 'C') # ชื่อจะเด้งมาที่นี่
        pdf.set_y(pdf.get_y() - 15)

    return bytes(pdf.output())

# --- 4. MAIN INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📝 ออกใบเสนอราคา", "➕ เพิ่มลูกค้าใหม่", "📦 เพิ่มสินค้าใหม่"])

# --- TAB 1: ออกใบเสนอราคา ---
with tab1:
    df_customers = fetch_customers()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. เลือกข้อมูลลูกค้า")
        # เมื่อคลิกเลือก ID ข้อมูลชื่อและที่อยู่ต้องเด้ง (Auto-fill)
        cust_list = ["-- เลือกจากฐานข้อมูล --"] + df_customers['id'].astype(str).tolist()
        sid = st.selectbox("ค้นหารหัสลูกค้า", options=cust_list)
        
        target = df_customers[df_customers['id'].astype(str) == sid].iloc[0] if sid != "-- เลือกจากฐานข้อมูล --" else {}
        name = st.text_input("ชื่อบริษัท/ลูกค้า", value=target.get('name', ''))
        addr = st.text_area("ที่อยู่จัดส่ง", value=target.get('address', ''), height=100)

    with col2:
        st.subheader("2. ข้อมูลผู้ลงนาม")
        s1 = st.text_input("ชื่อผู้อนุมัติ (ลูกค้า)", "")
        s2 = st.text_input("ชื่อพนักงานขาย", "")
        s3 = st.text_input("ชื่อผู้จัดการ", "")
        dno = st.text_input("เลขที่เอกสาร", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        v_on = st.checkbox("คิด VAT 7%", value=True)

    st.divider()
    
    # ตารางบันทึกรายการสินค้า
    st.subheader("3. รายการสินค้า")
    with st.expander("🔍 ดูรหัสสินค้าและราคาในคลัง"):
        st.dataframe(fetch_products(), use_container_width=True)

    grid = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20, 
                          num_rows="dynamic", use_container_width=True)
    
    # คำนวณเงิน
    df_grid = pd.DataFrame(grid)
    df_grid['qty_num'] = pd.to_numeric(df_grid['จำนวน'], errors='coerce').fillna(0)
    df_grid['price_num'] = pd.to_numeric(df_grid['ราคา'], errors='coerce').fillna(0)
    df_grid['รวมเงิน'] = df_grid['qty_num'] * df_grid['price_num']
    
    sub = int(df_grid['รวมเงิน'].sum())
    v_amt = int(sub * 0.07) if v_on else 0
    grand = sub + v_amt

    # ✅ ปุ่มพิมพ์ทันที (ไม่ต้องมี Pop-up เตือน)
    if name:
        pdf_bytes = create_pdf(dno, name, addr, df_grid, sub, v_amt, grand, [s1, s2, s3])
        st.download_button("🔥 คลิกที่นี่เพื่อพิมพ์/ดาวน์โหลด PDF", data=pdf_bytes, 
                           file_name=f"{dno}.pdf", mime="application/pdf", use_container_width=True)

# --- TAB 2: เพิ่มลูกค้าใหม่ (ห้ามตัด) ---
with tab2:
    st.subheader("บันทึกรายชื่อลูกค้าใหม่ลงฐานข้อมูล")
    with st.form("add_cust_form", clear_on_submit=True):
        new_id = st.text_input("รหัสลูกค้า (ID)")
        new_name = st.text_input("ชื่อบริษัท/ชื่อลูกค้า")
        new_addr = st.text_area("ที่อยู่")
        if st.form_submit_button("บันทึกข้อมูล"):
            if new_id and new_name:
                conn.table("customers").insert({"id": new_id, "name": new_name, "address": new_addr}).execute()
                st.success(f"บันทึก '{new_name}' สำเร็จ! ข้อมูลจะไปปรากฏในหน้าแรก")
                st.cache_data.clear() # ล้าง Cache เพื่อให้ข้อมูลใหม่เด้งขึ้นมา
            else:
                st.warning("กรุณากรอกรหัสและชื่อลูกค้า")

# --- TAB 3: เพิ่มสินค้าใหม่ (ห้ามตัด) ---
with tab3:
    st.subheader("บันทึกสินค้าใหม่ลงฐานข้อมูล")
    with st.form("add_prod_form", clear_on_submit=True):
        p_code = st.text_input("รหัสสินค้า")
        p_name = st.text_input("รายการสินค้า")
        p_unit = st.text_input("หน่วย")
        p_price = st.number_input("ราคาต่อหน่วย", min_value=0)
        if st.form_submit_button("บันทึกสินค้า"):
            if p_code and p_name:
                conn.table("products").insert({"code": p_code, "name": p_name, "unit": p_unit, "price": p_price}).execute()
                st.success(f"บันทึก '{p_name}' สำเร็จ!")
                st.cache_data.clear()
