import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. การตั้งค่าหน้าตาแอป ---
st.set_page_config(page_title="ระบบออกใบเสนอราคา", layout="wide")

# ดึงค่า Config (ตรวจสอบว่าพี่ตั้งค่าใน Render หรือยัง)
MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตรวจสอบ Environment Variables: SUPABASE_URL และ SUPABASE_KEY")
    st.stop()

# เชื่อมต่อ Supabase
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=MY_SUPABASE_URL,
        key=MY_SUPABASE_KEY
    )
except Exception as e:
    st.error(f"การเชื่อมต่อฐานข้อมูลล้มเหลว: {e}")
    st.stop()

# ฟังก์ชันดึงข้อมูลจากตาราง
def fetch_data(table_name):
    try:
        res = conn.table(table_name).select("*").execute()
        if res.data:
            return pd.DataFrame(res.data)
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- 2. ฟังก์ชันสร้าง PDF (แก้ตาม Error ที่พี่เจอ) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total):
    pdf = FPDF()
    pdf.add_page()
    
    # ดึงไฟล์ฟอนต์ที่พี่อัปโหลดไว้ (THSarabunNew.ttf)
    font_path = "THSarabunNew.ttf"
    
    if os.path.exists(font_path):
        # โหลดฟอนต์ไทย และตั้งชื่อเรียกในระบบว่า 'THSarabun'
        pdf.add_font('THSarabun', '', font_path)
        pdf.set_font('THSarabun', '', 18)
        current_font = 'THSarabun'
    else:
        # ถ้าหาไฟล์ไม่เจอ จะใช้ Arial แทน (แต่อาจจะขึ้น Error ภาษาไทยเหมือนเดิม)
        pdf.set_font("Arial", 'B', 16)
        current_font = 'Arial'
        st.warning(f"⚠️ คำเตือน: ไม่พบไฟล์ {font_path} ในระบบ PDF อาจจะอ่านภาษาไทยไม่ออก")

    # หัวเอกสาร
    pdf.cell(0, 15, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')
    
    pdf.set_font(current_font, '', 14)
    pdf.cell(0, 8, f"เลขที่เอกสาร: {doc_no}", 0, 1)
    pdf.cell(0, 8, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    # ข้อมูลลูกค้า
    pdf.set_font(current_font, 'B', 14)
    pdf.cell(0, 8, "ข้อมูลลูกค้า:", 0, 1)
    pdf.set_font(current_font, '', 14)
    pdf.cell(0, 8, f"ชื่อลูกค้า: {cust_name}", 0, 1)
    pdf.multi_cell(0, 8, f"ที่อยู่: {cust_addr}")
    pdf.ln(5)
    
    # ตารางสินค้า
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font(current_font, 'B', 14)
    pdf.cell(90, 10, "รายการ", 1, 0, 'C', True)
    pdf.cell(20, 10, "จำนวน", 1, 0, 'C', True)
    pdf.cell(35, 10, "ราคา/หน่วย", 1, 0, 'C', True)
    pdf.cell(45, 10, "รวมเงิน", 1, 1, 'C', True)
    
    pdf.set_font(current_font, '', 14)
    for _, row in df_items.iterrows():
        qty = float(row.get('จำนวน', 0))
        price = float(row.get('ราคา/หน่วย', 0))
        total_line = qty * price
        
        if total_line > 0:
            pdf.cell(90, 10, str(row.get('รายการ', '-')), 1)
            pdf.cell(20, 10, f"{qty:,.0f}", 1, 0, 'C')
            pdf.cell(35, 10, f"{price:,.0f}", 1, 0, 'R')
            pdf.cell(45, 10, f"{total_line:,.0f}", 1, 1, 'R')
            
    pdf.ln(5)
    
    # สรุปยอด
    pdf.set_font(current_font, 'B', 14)
    pdf.cell(145, 10, "รวมเงินก่อนภาษี:", 0, 0, 'R')
    pdf.cell(45, 10, f"{subtotal:,.0f} บาท", 0, 1, 'R')
    pdf.cell(145, 10, "ภาษีมูลค่าเพิ่ม (7%):", 0, 0, 'R')
    pdf.cell(45, 10, f"{vat:,.0f} บาท", 0, 1, 'R')
    pdf.cell(145, 10, "ยอดรวมสุทธิ:", 0, 0, 'R')
    pdf.cell(45, 10, f"{grand_total:,.0f} บาท", 0, 1, 'R')
    
    # แก้ Error 'bytearray' object has no attribute 'encode'
    # ห้ามใส่ .encode('latin-1') เด็ดขาดใน fpdf2
    return pdf.output()

# --- 3. หน้าจอการใช้งาน ---
st.title("📄 ระบบจัดการใบเสนอราคา (Full Version)")

t1, t2, t3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ข้อมูลลูกค้า", "📦 คลังสินค้า"])

with t1:
    df_customers = fetch_data("customers")
    
    col_1, col_2, col_3 = st.columns([2, 2, 1.5])
    with col_1:
        st.subheader("1. เลือกลูกค้า")
        c_list = ["-- เลือกรายชื่อลูกค้า --"]
        if not df_customers.empty:
            # ดึงคอลัมน์แรกมาเป็น ID เสมอ (ป้องกัน KeyError 'id')
            c_list += df_customers.iloc[:, 0].tolist()
            
        select_id = st.selectbox("รหัสลูกค้า", options=c_list)
        
        # ดึงข้อมูลลูกค้าอัตโนมัติ
        c_info = {}
        if select_id != "-- เลือกรายชื่อลูกค้า --":
            c_info = df_customers[df_customers.iloc[:, 0] == select_id].iloc[0].to_dict()
            
        cust_name = st.text_input("ชื่อลูกค้า", value=c_info.get('name', ''))
        cust_phone = st.text_input("เบอร์โทรศัพท์", value=c_info.get('phone', ''))

    with col_2:
        st.subheader("2. ข้อมูลจัดส่ง")
        cust_addr = st.text_area("ที่อยู่ลูกค้า", value=c_info.get('address', ''), height=122)

    with col_3:
        st.subheader("3. การตั้งค่า")
        doc_id = st.text_input("เลขที่เอกสาร", f"QT-{datetime.now().strftime('%Y%m%d-%H%M')}")
        v_on = st.checkbox("คิดภาษี VAT 7%", value=True)

    st.divider()

    # ตารางรายการสินค้า
    st.subheader("4. รายการสินค้า")
    grid_rows = [{"รายการ": "", "จำนวน": 0, "ราคา/หน่วย": 0}] * 8
    edited_data = st.data_editor(grid_rows, num_rows="dynamic", use_container_width=True)

    # คำนวณเงิน
    df_calc = pd.DataFrame(edited_data)
    df_calc['line_sum'] = pd.to_numeric(df_calc['จำนวน'], errors='coerce').fillna(0) * \
                          pd.to_numeric(df_calc['ราคา/หน่วย'], errors='coerce').fillna(0)
    
    total_raw = int(round(df_calc['line_sum'].sum()))
    total_vat = int(round(total_raw * 0.07)) if v_on else 0
    total_net = total_raw + total_vat

    st.divider()
    
    # แสดงยอดสรุปและปุ่ม PDF
    sum_1, sum_2 = st.columns([3, 1])
    with sum_2:
        st.write(f"ยอดรวม: **{total_raw:,}** บาท")
        st.write(f"ภาษี (7%): **{total_vat:,}** บาท")
        st.markdown(f"## **สุทธิ: {total_net:,} บาท**")
        
        if st.button("บันทึกและดาวน์โหลด PDF", type="primary"):
            try:
                pdf_output = create_pdf(doc_id, cust_name, cust_addr, df_calc, total_raw, total_vat, total_net)
                st.download_button(
                    label="📥 กดเพื่อดาวน์โหลด PDF",
                    data=pdf_output,
                    file_name=f"{doc_id}.pdf",
                    mime="application/pdf"
                )
                st.success("สร้างไฟล์ PDF สำเร็จ!")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสร้างไฟล์: {e}")

# TAB อื่นๆ สำหรับดูข้อมูล
with t2:
    st.header("รายชื่อลูกค้าในฐานข้อมูล")
    st.dataframe(df_customers, use_container_width=True)

with t3:
    st.header("รายการสินค้าในคลัง")
    df_p = fetch_data("products")
    st.dataframe(df_p, use_container_width=True)
