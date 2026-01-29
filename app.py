import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. การตั้งค่าระบบ ---
st.set_page_config(page_title="ระบบออกใบเสนอราคา", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่า SUPABASE_URL และ KEY ในหน้า Settings ของ Render")
    st.stop()

# เชื่อมต่อฐานข้อมูล
try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"การเชื่อมต่อผิดพลาด: {e}")
    st.stop()

# ฟังก์ชันดึงข้อมูล
def fetch_data(table_name):
    try:
        res = conn.table(table_name).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 2. ฟังก์ชันสร้าง PDF (แก้ตามรูปที่พี่ส่งมา) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total):
    # สร้างออบเจกต์ PDF
    pdf = FPDF()
    pdf.add_page()
    
    # ดึงไฟล์ฟอนต์ที่พี่อัปโหลดไว้ใน GitHub (รูปที่ 3)
    font_file = "THSarabunNew.ttf"
    
    if os.path.exists(font_file):
        # ถ้ามีไฟล์ฟอนต์ ให้โหลดใช้งาน (แก้ Error รูปที่ 2)
        pdf.add_font('THSarabun', '', font_file, uni=True)
        pdf.set_font('THSarabun', '', 20)
        use_font = 'THSarabun'
    else:
        # ถ้าหาไม่เจอจริงๆ ให้ใช้ Arial (แต่จะ Error ภาษาไทย)
        pdf.set_font("Arial", 'B', 16)
        use_font = 'Arial'
        st.error(f"ไม่พบไฟล์ {font_file} ในโฟลเดอร์หลัก! กรุณาตรวจสอบการอัปโหลด")

    # ส่วนหัว
    pdf.cell(0, 15, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')
    
    pdf.set_font(use_font, '', 14)
    pdf.cell(0, 10, f"เลขที่เอกสาร: {doc_no}", 0, 1)
    pdf.cell(0, 10, f"วันที่ออกเอกสาร: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    # ข้อมูลลูกค้า
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(0, 10, "ข้อมูลลูกค้า / Customer Information:", 0, 1)
    pdf.set_font(use_font, '', 14)
    pdf.cell(0, 10, f"ชื่อลูกค้า: {cust_name}", 0, 1)
    pdf.multi_cell(0, 10, f"ที่อยู่: {cust_addr}")
    pdf.ln(10)
    
    # ตารางรายการสินค้า
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(90, 12, "รายการ (Description)", 1, 0, 'C', True)
    pdf.cell(20, 12, "จำนวน", 1, 0, 'C', True)
    pdf.cell(35, 12, "ราคา/หน่วย", 1, 0, 'C', True)
    pdf.cell(45, 12, "รวมเงิน", 1, 1, 'C', True)
    
    pdf.set_font(use_font, '', 14)
    for index, row in df_items.iterrows():
        # ตรวจสอบว่ามีข้อมูลจริงถึงจะพิมพ์ลง PDF
        try:
            name = str(row.get('รายการ', ''))
            qty = float(row.get('จำนวน', 0))
            price = float(row.get('ราคา/หน่วย', 0))
            line_total = qty * price
            
            if line_total > 0 or name != "":
                pdf.cell(90, 12, name, 1)
                pdf.cell(20, 12, f"{qty:,.0f}", 1, 0, 'C')
                pdf.cell(35, 12, f"{price:,.0f}", 1, 0, 'R')
                pdf.cell(45, 12, f"{line_total:,.0f}", 1, 1, 'R')
        except:
            continue
            
    pdf.ln(5)
    
    # สรุปเงิน
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(145, 10, "ยอดรวม (Subtotal):", 0, 0, 'R')
    pdf.cell(45, 10, f"{subtotal:,.0f} บาท", 0, 1, 'R')
    
    pdf.cell(145, 10, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(45, 10, f"{vat:,.0f} บาท", 0, 1, 'R')
    
    pdf.set_font(use_font, 'B', 16)
    pdf.cell(145, 12, "ยอดรวมสุทธิ (Grand Total):", 0, 0, 'R')
    pdf.cell(45, 12, f"{grand_total:,.0f} บาท", 0, 1, 'R')
    
    # แก้ Error รูปที่ 1: ใช้ .output() โดยไม่ต้อง .encode()
    return pdf.output()

# --- 3. หน้าจอการใช้งาน (UI) ---
st.title("📄 ระบบจัดการใบเสนอราคา")

tab1, tab2, tab3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ข้อมูลลูกค้า", "📦 คลังสินค้า"])

with tab1:
    df_customers = fetch_data("customers")
    
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        st.subheader("ส่วนที่ 1: ข้อมูลลูกค้า")
        c_list = ["-- เลือกรายชื่อ --"]
        if not df_customers.empty:
            # ใช้คอลัมน์แรกสุดเป็น ID ไม่ว่าจะชื่ออะไรก็ตาม (แก้ปัญหา KeyError)
            c_list += df_customers.iloc[:, 0].tolist()
            
        selected_cust = st.selectbox("เลือกรหัสลูกค้า", options=c_list)
        
        # ดึงข้อมูลมาเติม
        cust_data = {}
        if selected_cust != "-- เลือกรายชื่อ --":
            cust_data = df_customers[df_customers.iloc[:, 0] == selected_cust].iloc[0].to_dict()
            
        c_name = st.text_input("ชื่อลูกค้า/บริษัท", value=cust_data.get('name', ''))
        c_addr = st.text_area("ที่อยู่", value=cust_data.get('address', ''), height=100)

    with col_b:
        st.subheader("ส่วนที่ 2: ตั้งค่าเอกสาร")
        d_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d-%H%M')}")
        v_check = st.checkbox("ต้องการคำนวณ VAT 7%", value=True)

    st.divider()
    
    # ตารางกรอกสินค้า (แบบเต็มๆ ชัดๆ)
    st.subheader("ส่วนที่ 3: รายการสินค้า")
    grid_data = [{"รายการ": "", "จำนวน": 0, "ราคา/หน่วย": 0}] * 8
    input_df = st.data_editor(grid_data, num_rows="dynamic", use_container_width=True)

    # คำนวณเงิน
    res_df = pd.DataFrame(input_df)
    res_df['total'] = pd.to_numeric(res_df['จำนวน'], errors='coerce').fillna(0) * \
                      pd.to_numeric(res_df['ราคา/หน่วย'], errors='coerce').fillna(0)
    
    sub_amt = int(round(res_df['total'].sum()))
    vat_amt = int(round(sub_amt * 0.07)) if v_check else 0
    total_amt = sub_amt + vat_amt

    # สรุปยอด
    st.divider()
    c1, c2 = st.columns([3, 1])
    with c2:
        st.write(f"ยอดรวม: {sub_amt:,} บาท")
        st.write(f"ภาษี 7%: {vat_amt:,} บาท")
        st.markdown(f"### **ยอดสุทธิ: {total_amt:,} บาท**")
        
        # ปุ่มดำเนินการ
        if st.button("บันทึกและดาวน์โหลด PDF", type="primary"):
            try:
                pdf_data = create_pdf(d_no, c_name, c_addr, res_df, sub_amt, vat_amt, total_amt)
                st.download_button(
                    label="📥 กดที่นี่เพื่อโหลดไฟล์ PDF",
                    data=pdf_data,
                    file_name=f"{d_no}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

# TAB อื่นๆ (พี่เอาไว้จัดการฐานข้อมูลได้เลย)
with tab2:
    st.header("จัดการฐานข้อมูลลูกค้า")
    st.dataframe(df_customers, use_container_width=True)

with tab3:
    st.header("จัดการฐานข้อมูลสินค้า")
    df_p = fetch_data("products")
    st.dataframe(df_p, use_container_width=True)
