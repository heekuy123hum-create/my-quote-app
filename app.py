import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. การตั้งค่าหน้าตาแอป (UI CONFIG) ---
st.set_page_config(page_title="ระบบออกใบเสนอราคามาตรฐาน", layout="wide")

# ดึงค่า Config จาก Environment Variables
MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่า SUPABASE_URL และ SUPABASE_KEY ในระบบให้เรียบร้อย")
    st.stop()

# เชื่อมต่อฐานข้อมูล Supabase
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=MY_SUPABASE_URL,
        key=MY_SUPABASE_KEY
    )
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
    st.stop()

# --- 2. ฟังก์ชันจัดการข้อมูล (DATABASE LOGIC) ---
def fetch_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- 3. ฟังก์ชันสร้าง PDF (รองรับภาษาไทยเต็มรูปแบบ) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total):
    pdf = FPDF()
    pdf.add_page()
    
    # โหลดฟอนต์ไทย (ต้องมีไฟล์ THSarabunNew.ttf ในโปรเจกต์บน GitHub)
    try:
        pdf.add_font('THSarabun', '', 'THSarabunNew.ttf')
        pdf.set_font('THSarabun', '', 24)
    except:
        # ถ้าหาไฟล์ฟอนต์ไม่เจอ จะใช้ Arial แทน (แต่อาจจะอ่านไทยไม่ออก)
        pdf.set_font("Arial", 'B', 16)
    
    # ส่วนหัวใบเสนอราคา
    pdf.cell(0, 15, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')
    
    pdf.set_font('THSarabun' if 'THSarabun' in pdf.fonts else "Arial", '', 15)
    pdf.cell(0, 10, f"เลขที่เอกสาร: {doc_no}", 0, 1)
    pdf.cell(0, 10, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    # ข้อมูลลูกค้า
    pdf.set_font('THSarabun' if 'THSarabun' in pdf.fonts else "Arial", 'B', 15)
    pdf.cell(0, 10, "ข้อมูลลูกค้า:", 0, 1)
    pdf.set_font('THSarabun' if 'THSarabun' in pdf.fonts else "Arial", '', 15)
    pdf.cell(0, 10, f"ชื่อลูกค้า: {cust_name}", 0, 1)
    pdf.multi_cell(0, 10, f"ที่อยู่: {cust_addr}")
    pdf.ln(10)
    
    # ส่วนหัวตารางรายการสินค้า
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('THSarabun' if 'THSarabun' in pdf.fonts else "Arial", 'B', 15)
    pdf.cell(80, 12, "รายการ", 1, 0, 'C', True)
    pdf.cell(25, 12, "จำนวน", 1, 0, 'C', True)
    pdf.cell(40, 12, "ราคา/หน่วย", 1, 0, 'C', True)
    pdf.cell(45, 12, "รวมเงิน", 1, 1, 'C', True)
    
    # รายการสินค้าจากตาราง
    pdf.set_font('THSarabun' if 'THSarabun' in pdf.fonts else "Arial", '', 15)
    for _, row in df_items.iterrows():
        qty = float(row.get('จำนวน', 0))
        price = float(row.get('ราคา/หน่วย', 0))
        total_line = qty * price
        
        if total_line > 0:
            pdf.cell(80, 12, str(row.get('รายการ', '-')), 1)
            pdf.cell(25, 12, f"{qty:,.0f}", 1, 0, 'C')
            pdf.cell(40, 12, f"{price:,.0f}", 1, 0, 'R')
            pdf.cell(45, 12, f"{total_line:,.0f}", 1, 1, 'R')
            
    pdf.ln(5)
    
    # สรุปยอดเงิน (เลขกลม)
    pdf.set_font('THSarabun' if 'THSarabun' in pdf.fonts else "Arial", 'B', 15)
    pdf.cell(145, 10, "รวมเงิน:", 0, 0, 'R')
    pdf.cell(45, 10, f"{subtotal:,} บาท", 0, 1, 'R')
    
    pdf.cell(145, 10, "ภาษีมูลค่าเพิ่ม (7%):", 0, 0, 'R')
    pdf.cell(45, 10, f"{vat:,} บาท", 0, 1, 'R')
    
    pdf.set_font('THSarabun' if 'THSarabun' in pdf.fonts else "Arial", 'B', 18)
    pdf.cell(145, 12, "ยอดรวมสุทธิ:", 0, 0, 'R')
    pdf.cell(45, 12, f"{grand_total:,} บาท", 0, 1, 'R')
    
    return pdf.output()

# --- 4. หน้าจอหลัก (MAIN UI) ---
st.title("📄 ระบบออกใบเสนอราคา (Full Version)")

tab_doc, tab_cust, tab_prod = st.tabs(["📝 ออกใบเสนอราคา", "👥 จัดการลูกค้า", "📦 จัดการสินค้า"])

# --- TAB: ออกใบเสนอราคา ---
with tab_doc:
    df_customers = fetch_data("customers")
    df_products = fetch_data("products")

    with st.container():
        col_c1, col_c2, col_c3 = st.columns([1.5, 2, 1.5])
        
        with col_c1:
            st.subheader("ข้อมูลลูกค้า")
            # ป้องกันปัญหาชื่อคอลัมน์ไม่ตรง
            c_options = ["-- เลือกรหัสลูกค้า --"]
            if not df_customers.empty:
                c_options += df_customers.iloc[:, 0].tolist()
            
            selected_id = st.selectbox("เลือก ID ลูกค้า", options=c_options)
            
            c_info = {}
            if selected_id != "-- เลือกรหัสลูกค้า --" and not df_customers.empty:
                # ค้นหาข้อมูลจากแถวที่ ID ตรงกัน
                c_info = df_customers[df_customers.iloc[:, 0] == selected_id].iloc[0].to_dict()
            
            cust_name = st.text_input("ชื่อผู้ติดต่อ/ลูกค้า", value=c_info.get('name', ''))
            cust_phone = st.text_input("เบอร์โทรศัพท์", value=c_info.get('phone', ''))

        with col_c2:
            st.subheader("ที่อยู่เอกสาร")
            cust_addr = st.text_area("ที่อยู่โดยละเอียด", value=c_info.get('address', ''), height=122)

        with col_c3:
            st.subheader("ข้อมูลเอกสาร")
            doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d-%H%M')}")
            use_vat = st.checkbox("คิดภาษี (VAT 7%)", value=True)

    st.divider()

    # ตารางรายการสินค้า
    st.subheader("รายการสินค้า")
    if 'items_rows' not in st.session_state:
        st.session_state.items_rows = [{"รหัส": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา/หน่วย": 0, "ส่วนลด": 0}] * 10

    edited_df = st.data_editor(st.session_state.items_rows, num_rows="dynamic", use_container_width=True)

    # คำนวณยอดเงิน (Round เป็นเลขกลม)
    calc_df = pd.DataFrame(edited_df)
    calc_df['total_line'] = (pd.to_numeric(calc_df['จำนวน'], errors='coerce').fillna(0) * pd.to_numeric(calc_df['ราคา/หน่วย'], errors='coerce').fillna(0)) - \
                            pd.to_numeric(calc_df['ส่วนลด'], errors='coerce').fillna(0)
    
    sub_total = int(round(calc_df['total_line'].sum()))
    vat_val = int(round(sub_total * 0.07)) if use_vat else 0
    grand_total = sub_total + vat_val

    st.divider()
    
    col_sum1, col_sum2 = st.columns([2, 1])
    with col_sum2:
        st.write(f"ยอดรวมก่อนภาษี: **{sub_total:,}** บาท")
        st.write(f"ภาษีมูลค่าเพิ่ม (7%): **{vat_val:,}** บาท")
        st.markdown(f"## **ยอดสุทธิ: {grand_total:,} บาท**")
        
        # ปุ่มสร้าง PDF และดาวน์โหลด
        if st.button("บันทึกข้อมูลและเตรียมไฟล์ PDF", type="primary"):
            try:
                pdf_output = create_pdf(doc_no, cust_name, cust_addr, calc_df, sub_total, vat_val, grand_total)
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ PDF",
                    data=pdf_output,
                    file_name=f"{doc_no}.pdf",
                    mime="application/pdf"
                )
                st.success("สร้างไฟล์สำเร็จ! กรุณากดปุ่มดาวน์โหลดด้านบน")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {e}")

# --- TAB: จัดการข้อมูลลูกค้า ---
with tab_cust:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    with st.form("add_customer", clear_on_submit=True):
        c_id = st.text_input("รหัสลูกค้า (ID)")
        c_name = st.text_input("ชื่อลูกค้า/บริษัท")
        c_phone = st.text_input("เบอร์โทรศัพท์")
        c_addr = st.text_area("ที่อยู่")
        if st.form_submit_button("บันทึกข้อมูลลง Cloud"):
            if c_id and c_name:
                conn.table("customers").upsert({"id": c_id, "name": c_name, "phone": c_phone, "address": c_addr}).execute()
                st.success("บันทึกข้อมูลสำเร็จ")
                st.rerun()

# --- TAB: จัดการข้อมูลสินค้า ---
with tab_prod:
    st.header("📦 รายการสินค้าในคลัง")
    st.dataframe(df_products, use_container_width=True)
