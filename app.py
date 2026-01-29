import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. การตั้งค่าหน้าตาแอป ---
st.set_page_config(page_title="ระบบออกใบเสนอราคามาตรฐาน", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่าความปลอดภัยในระบบให้เรียบร้อย (Environment Variables)")
    st.stop()

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
    st.stop()

def fetch_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- 2. ฟังก์ชันสร้าง PDF (แก้ไขให้รองรับโครงสร้างตาราง) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total):
    pdf = FPDF()
    pdf.add_page()
    # หมายเหตุ: สำหรับภาษาไทยต้องมีการโหลดฟอนต์ .ttf เพิ่มเติม 
    # แต่เบื้องต้นปรับโครงสร้างให้รองรับข้อมูลจากตาราง editor
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "QUOTATION", 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"No: {doc_no}", 0, 1)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.cell(0, 10, f"Customer: {cust_name}", 0, 1)
    pdf.multi_cell(0, 10, f"Address: {cust_addr}")
    pdf.ln(5)
    
    # ตารางรายการสินค้า
    pdf.cell(100, 10, "Description", 1)
    pdf.cell(30, 10, "Qty", 1, 0, 'C')
    pdf.cell(30, 10, "Price", 1, 0, 'C')
    pdf.cell(30, 10, "Total", 1, 1, 'C')
    
    for _, row in df_items.iterrows():
        if row['total_line'] > 0:
            pdf.cell(100, 10, str(row['รายการ']), 1)
            pdf.cell(30, 10, str(row['จำนวน']), 1, 0, 'C')
            pdf.cell(30, 10, f"{row['ราคา/หน่วย']:,}", 1, 0, 'R')
            pdf.cell(30, 10, f"{row['total_line']:,}", 1, 1, 'R')
            
    pdf.ln(5)
    pdf.cell(160, 10, "Subtotal:", 0, 0, 'R')
    pdf.cell(30, 10, f"{subtotal:,}", 0, 1, 'R')
    pdf.cell(160, 10, "VAT:", 0, 0, 'R')
    pdf.cell(30, 10, f"{vat:,}", 0, 1, 'R')
    pdf.cell(160, 10, "Grand Total:", 0, 0, 'R')
    pdf.cell(30, 10, f"{grand_total:,}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. หน้าจอหลัก ---
st.title("📋 ระบบออกใบเสนอราคาดิจิทัล")
tab_doc, tab_cust, tab_prod = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ข้อมูลลูกค้า", "📦 คลังสินค้า"])

with tab_doc:
    df_customers = fetch_data("customers")
    df_products = fetch_data("products")

    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col1:
        st.subheader("ข้อมูลลูกค้า")
        c_options = ["-- เลือกรหัสลูกค้า --"]
        if not df_customers.empty: c_options += df_customers['id'].tolist()
        selected_id = st.selectbox("เลือกรหัสลูกค้า", options=c_options)
        c_info = df_customers[df_customers['id'] == selected_id].iloc[0] if selected_id != "-- เลือกรหัสลูกค้า --" else {}
        cust_name = st.text_input("ชื่อลูกค้า", value=c_info.get('name', ''))
        cust_phone = st.text_input("เบอร์โทรศัพท์", value=c_info.get('phone', ''))

    with col2:
        st.subheader("ที่อยู่จัดส่ง")
        cust_addr = st.text_area("ที่อยู่", value=c_info.get('address', ''), height=122)

    with col3:
        st.subheader("ข้อมูลเอกสาร")
        doc_no = st.text_input("เลขที่เอกสาร", f"QT-{datetime.now().strftime('%Y%m%d-%H%M')}")
        use_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)

    st.divider()

    # ตารางสินค้าแบบพัฒนาแล้ว (เพิ่มปุ่มดึงข้อมูลสินค้าอัตโนมัติ)
    st.subheader("รายการสินค้า")
    if 'rows' not in st.session_state:
        st.session_state.rows = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา/หน่วย": 0, "ส่วนลด": 0}] * 5

    edited_df = st.data_editor(st.session_state.rows, num_rows="dynamic", use_container_width=True)

    if st.button("🔄 ดึงข้อมูลจากรหัสสินค้าที่พิมพ์"):
        p_data = df_products.set_index('code').to_dict('index') if not df_products.empty else {}
        updated_rows = []
        for r in edited_df:
            code = r.get('รหัสสินค้า')
            if code in p_data:
                r.update({"รายการ": p_data[code]['description'], "หน่วย": p_data[code]['unit'], "ราคา/หน่วย": p_data[code]['price']})
            updated_rows.append(r)
        st.session_state.rows = updated_rows
        st.rerun()

    # คำนวณเงิน
    calc_df = pd.DataFrame(edited_df)
    calc_df['total_line'] = (pd.to_numeric(calc_df['จำนวน'], errors='coerce').fillna(0) * pd.to_numeric(calc_df['ราคา/หน่วย'], errors='coerce').fillna(0)) - pd.to_numeric(calc_df['ส่วนลด'], errors='coerce').fillna(0)
    
    sub_total = int(round(calc_df['total_line'].sum()))
    vat_val = int(round(sub_total * 0.07)) if use_vat else 0
    grand_total = sub_total + vat_val

    st.divider()
    res_col1, res_col2 = st.columns([2, 1])
    with res_col2:
        st.write(f"ยอดรวม: **{sub_total:,}** บาท")
        st.write(f"ภาษี (7%): **{vat_val:,}** บาท")
        st.markdown(f"### **ยอดรวมสุทธิ: {grand_total:,} บาท**")
        
        if st.button("บันทึกข้อมูลและเตรียมไฟล์ PDF"):
            pdf_bytes = create_pdf(doc_no, cust_name, cust_addr, calc_df, sub_total, vat_val, grand_total)
            st.download_button(label="📥 ดาวน์โหลดใบเสนอราคา (PDF)", data=pdf_bytes, file_name=f"{doc_no}.pdf", mime="application/pdf")

# ส่วนจัดการฐานข้อมูล (คงไว้เหมือนเดิม)
with tab_cust:
    st.header("จัดการรายชื่อลูกค้า")
    with st.form("c_form"):
        ci = st.text_input("รหัสลูกค้า")
        cn = st.text_input("ชื่อลูกค้า")
        ca = st.text_area("ที่อยู่")
        if st.form_submit_button("บันทึก"):
            conn.table("customers").upsert({"id": ci, "name": cn, "address": ca}).execute()
            st.success("บันทึกสำเร็จ")
            st.rerun()

with tab_prod:
    st.header("จัดการรายการสินค้า")
    with st.form("p_form"):
        pi = st.text_input("รหัสสินค้า")
        pd = st.text_input("รายละเอียด")
        pu = st.text_input("หน่วย")
        pp = st.number_input("ราคา", min_value=0)
        if st.form_submit_button("บันทึก"):
            conn.table("products").upsert({"code": pi, "description": pd, "unit": pu, "price": pp}).execute()
            st.success("บันทึกสำเร็จ")
            st.rerun()
    st.dataframe(df_products, use_container_width=True)
