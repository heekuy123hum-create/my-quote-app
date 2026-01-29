import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบใบเสนอราคา (Full System)", layout="wide")

# เชื่อมต่อ Supabase
MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"เชื่อมต่อฐานข้อมูลล้มเหลว: {e}")
    st.stop()

# --- 2. ฟังก์ชันดึงข้อมูล (จดจำค่าไว้ใน Cache) ---
@st.cache_data(ttl=60)
def get_customers():
    res = conn.table("customers").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['id', 'name', 'address'])

@st.cache_data(ttl=60)
def get_products():
    res = conn.table("products").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['code', 'name', 'unit', 'price'])

# --- 3. ฟังก์ชันสร้าง PDF (ถอดแบบ A4 Chrome ของพี่เป๊ะๆ) ---
def create_pdf(doc_no, c_name, c_addr, df_items, subtotal, vat, grand_total, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # ฟอนต์ไทยที่พี่โหลดไว้
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # โลโก้ (ตรวจเช็กไฟล์)
    logo_file = next((f"logo.{ext}" for ext in ['png','jpg','jpeg'] if os.path.exists(f"logo.{ext}")), None)
    y_start = 35 if logo_file else 10
    if logo_file:
        pdf.image(logo_file, x=10, y=10, w=30)

    # หัวเอกสาร
    pdf.set_y(y_start)
    pdf.set_font(use_f, 'B', 22)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R')

    # ข้อมูลลูกค้า
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(120, 7, "ข้อมูลลูกค้า (Customer Details):", 0, 0)
    pdf.set_font(use_f, '', 14)
    pdf.cell(0, 7, f"เลขที่: {doc_no}", 0, 1, 'R')
    pdf.cell(120, 7, f"ชื่อลูกค้า: {c_name}", 0, 0)
    pdf.cell(0, 7, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 7, f"ที่อยู่: {c_addr}")
    pdf.ln(2)

    # ตาราง 20 แถว (h=7.5 เพื่อไม่ให้ทับลายเซ็น)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font(use_f, 'B', 12)
    h = 7.5
    w = [10, 25, 70, 15, 15, 25, 30]
    headers = ["ลำดับ", "รหัสสินค้า", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "รวมเงิน"]
    for i in range(7): pdf.cell(w[i], h, headers[i], 1, 0, 'C', True)
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
            pdf.cell(w[j], h, d[j], 1, 0, align)
        pdf.ln()

    # สรุปเงิน
    pdf.ln(2); pdf.set_font(use_f, 'B', 14); label_w = sum(w[:-1])
    pdf.cell(label_w, 7, "รวมเงิน (Sub Total):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{subtotal:,.0f}", 'B', 1, 'R')
    pdf.cell(label_w, 7, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{vat:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 16); pdf.set_text_color(200, 0, 0)
    pdf.cell(label_w, 8, "ยอดรวมทั้งสิ้น:", 0, 0, 'R'); pdf.cell(w[-1], 8, f"{grand_total:,.0f} THB", 'B', 1, 'R')

    # ส่วนลายเซ็น 3 ช่อง (ดึงชื่อคนเซ็นมาใส่)
    pdf.set_y(-45); pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 11)
    titles = ["ผู้อนุมัติสั่งซื้อ", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    for i in range(3):
        pdf.set_xy(10 + (i*65), pdf.get_y())
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.cell(60, 5, f"{titles[i]}", 0, 1, 'C')
        pdf.cell(60, 5, f"( {sigs[i]} )", 0, 1, 'C') # ใส่ชื่อคนที่กรอก
        pdf.set_y(pdf.get_y() - 15)

    return bytes(pdf.output())

# --- 4. หน้าจอ UI (เชื่อมข้อมูลครบถ้วน) ---
df_customers = get_customers()
df_products = get_products()

# ส่วนที่ 1: ข้อมูลลูกค้า (คลิกแล้วต้องเด้ง)
st.subheader("👥 ข้อมูลลูกค้า (Customer Information)")
col_c1, col_c2 = st.columns([1, 2])

with col_c1:
    cust_options = ["-- เลือกรหัสลูกค้า --"] + df_customers['id'].astype(str).tolist()
    selected_cust_id = st.selectbox("เลือกรหัสลูกค้า", options=cust_options)

# ค้นหาข้อมูลลูกค้าเมื่อมีการเลือก
if selected_cust_id != "-- เลือกรหัสลูกค้า --":
    customer_data = df_customers[df_customers['id'].astype(str) == selected_cust_id].iloc[0]
    default_name = customer_data['name']
    default_addr = customer_data['address']
else:
    default_name = ""
    default_addr = ""

c_name = st.text_input("ชื่อบริษัท / ชื่อลูกค้า", value=default_name)
c_addr = st.text_area("ที่อยู่จัดส่ง / ที่อยู่ออกใบกำกับภาษี", value=default_addr, height=100)

st.divider()

# ส่วนที่ 2: รายการสินค้าและลายเซ็น
col_m1, col_m2 = st.columns([2, 1])

with col_m2:
    st.subheader("✍️ ข้อมูลการเซ็นชื่อ")
    sig_approver = st.text_input("ชื่อผู้อนุมัติ (ลูกค้า)", value="", placeholder="กรอกชื่อคนเซ็น")
    sig_sales = st.text_input("ชื่อพนักงานขาย", value="", placeholder="กรอกชื่อคนเซ็น")
    sig_manager = st.text_input("ชื่อผู้จัดการฝ่ายขาย", value="", placeholder="กรอกชื่อคนเซ็น")
    doc_number = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
    vat_check = st.checkbox("คิดภาษี VAT 7%", value=True)

with col_m1:
    st.subheader("📦 รายการสินค้า (Products)")
    # แสดงตารางอ้างอิงให้คลิกดูง่ายๆ
    with st.expander("🔍 คลิกเพื่อดูรายการสินค้าในคลัง (สำหรับก๊อปปี้รหัส)"):
        st.dataframe(df_products, use_container_width=True)

    # ตารางกรอกข้อมูล (Data Editor)
    init_data = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20
    edited_data = st.data_editor(init_data, num_rows="dynamic", use_container_width=True)

# --- 5. การคำนวณยอดเงิน ---
df_grid = pd.DataFrame(edited_data)
df_grid['qty_num'] = pd.to_numeric(df_grid['จำนวน'], errors='coerce').fillna(0)
df_grid['price_num'] = pd.to_numeric(df_grid['ราคา'], errors='coerce').fillna(0)
df_grid['รวมเงิน'] = df_grid['qty_num'] * df_grid['price_num']

subtotal = int(df_grid['รวมเงิน'].sum())
vat_amount = int(subtotal * 0.07) if vat_check else 0
grand_total = subtotal + vat_amount

# --- 6. ปุ่มกดสร้าง PDF ---
st.divider()
col_btn1, col_btn2 = st.columns([3, 1])
with col_btn2:
    st.write(f"**ยอดรวมสุทธิ:** {grand_total:,.0f} บาท")
    if st.button("🔥 บันทึกและพิมพ์ PDF", type="primary", use_container_width=True):
        if not c_name:
            st.warning("พี่ลืมกรอกชื่อลูกค้านะครับ!")
        else:
            sigs = [sig_approver, sig_sales, sig_manager]
            pdf_bytes = create_pdf(doc_number, c_name, c_addr, df_grid, subtotal, vat_amount, grand_total, sigs)
            st.download_button("📥 ดาวน์โหลดใบเสนอราคา", data=pdf_bytes, file_name=f"{doc_number}.pdf", mime="application/pdf")
