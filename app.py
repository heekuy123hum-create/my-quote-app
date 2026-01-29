import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. SETUP ระบบ ---
st.set_page_config(page_title="ระบบออกใบเสนอราคามาตรฐาน", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่า SUPABASE_URL และ SUPABASE_KEY ในระบบให้เรียบร้อย")
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

# --- 2. ฟังก์ชันสร้าง PDF (แก้ไขจุดที่ทำให้เกิด Invalid binary data) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total):
    pdf = FPDF()
    pdf.add_page()
    
    # ดึงไฟล์ฟอนต์ที่พี่อัปโหลดไว้ (THSarabunNew.ttf)
    font_path = "THSarabunNew.ttf"
    
    if os.path.exists(font_path):
        # โหลดฟอนต์ตัวธรรมดา และตัวหนา (ใช้ไฟล์เดียวกันได้)
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path) 
        use_font = 'THSarabun'
    else:
        pdf.set_font("Arial", '', 14)
        use_font = 'Arial'
        st.warning("⚠️ ไม่พบไฟล์ฟอนต์ THSarabunNew.ttf ในระบบ")

    # หัวเอกสาร
    pdf.set_font(use_font, 'B', 22)
    pdf.cell(0, 15, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')
    
    pdf.set_font(use_font, '', 15)
    pdf.cell(0, 10, f"เลขที่: {doc_no if doc_no else '-'}", 0, 1)
    pdf.cell(0, 10, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font(use_font, 'B', 16)
    pdf.cell(0, 10, "ข้อมูลลูกค้า:", 0, 1)
    pdf.set_font(use_font, '', 15)
    pdf.cell(0, 10, f"ชื่อ: {cust_name if cust_name else '-'}", 0, 1)
    pdf.multi_cell(0, 10, f"ที่อยู่: {cust_addr if cust_addr else '-'}")
    pdf.ln(10)
    
    # ตารางรายการสินค้า
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_font, 'B', 15)
    pdf.cell(90, 12, "รายการ", 1, 0, 'C', True)
    pdf.cell(20, 12, "จำนวน", 1, 0, 'C', True)
    pdf.cell(35, 12, "ราคา/หน่วย", 1, 0, 'C', True)
    pdf.cell(45, 12, "รวมเงิน", 1, 1, 'C', True)
    
    pdf.set_font(use_font, '', 15)
    for _, row in df_items.iterrows():
        desc = str(row.get('รายการ', '-')) if row.get('รายการ') else "-"
        qty = float(row.get('จำนวน', 0))
        price = float(row.get('ราคา/หน่วย', 0))
        total = qty * price
        
        pdf.cell(90, 12, desc, 1)
        pdf.cell(20, 12, f"{qty:,.0f}", 1, 0, 'C')
        pdf.cell(35, 12, f"{price:,.0f}", 1, 0, 'R')
        pdf.cell(45, 12, f"{total:,.0f}", 1, 1, 'R')
            
    pdf.ln(5)
    pdf.set_font(use_font, 'B', 16)
    pdf.cell(145, 10, "รวมเงิน:", 0, 0, 'R')
    pdf.cell(45, 10, f"{subtotal:,.0f} บาท", 0, 1, 'R')
    pdf.cell(145, 10, "ภาษี (7%):", 0, 0, 'R')
    pdf.cell(45, 10, f"{vat:,.0f} บาท", 0, 1, 'R')
    pdf.cell(145, 12, "ยอดสุทธิ:", 0, 0, 'R')
    pdf.cell(45, 12, f"{grand_total:,.0f} บาท", 0, 1, 'R')
    
    # สำคัญที่สุด: แปลง bytearray ให้เป็น bytes เพื่อป้องกัน Invalid binary data format
    return bytes(pdf.output())

# --- 3. UI ---
st.title("📄 ระบบออกใบเสนอราคา (Full Version)")

t1, t2, t3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 จัดการลูกค้า", "📦 จัดการสินค้า"])

with t1:
    df_c = fetch_data("customers")
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    
    with col1:
        st.subheader("ข้อมูลลูกค้า")
        c_list = ["-- เลือกรายชื่อ --"]
        if not df_c.empty:
            c_list += df_c.iloc[:, 0].tolist()
        
        sid = st.selectbox("รหัสลูกค้า", options=c_list)
        info = df_c[df_c.iloc[:, 0] == sid].iloc[0] if sid != "-- เลือกรายชื่อ --" else {}
        name = st.text_input("ชื่อลูกค้า", value=info.get('name', ''))

    with col2:
        st.subheader("ที่อยู่")
        addr = st.text_area("ที่อยู่จัดส่ง", value=info.get('address', ''), height=122)

    with col3:
        st.subheader("เอกสาร")
        dno = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%Y%m%d-%H%M')}")
        vat_on = st.checkbox("คิดภาษี VAT 7%", value=True)

    st.divider()
    
    # ตารางสินค้า (ใส่ 5 แถวเริ่มต้นให้ทดสอบได้เลย)
    grid = st.data_editor([{"รายการ": "", "จำนวน": 0, "ราคา/หน่วย": 0}] * 5, num_rows="dynamic", use_container_width=True)
    df_res = pd.DataFrame(grid)
    df_res['total'] = pd.to_numeric(df_res['จำนวน'], errors='coerce').fillna(0) * \
                      pd.to_numeric(df_res['ราคา/หน่วย'], errors='coerce').fillna(0)
    
    sub = int(round(df_res['total'].sum()))
    v_val = int(round(sub * 0.07)) if vat_on else 0
    grand = sub + v_val

    st.divider()
    if st.button("เตรียมไฟล์ PDF", type="primary"):
        try:
            # เรียกฟังก์ชันที่คืนค่าเป็น bytes
            pdf_data = create_pdf(dno, name, addr, df_res, sub, v_val, grand)
            
            # ส่งค่า bytes เข้า download_button
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์ PDF",
                data=pdf_data,
                file_name=f"{dno}.pdf",
                mime="application/pdf"
            )
            st.success("สร้างไฟล์สำเร็จ!")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# TAB อื่นๆ
with t2:
    st.header("รายชื่อลูกค้า")
    st.dataframe(df_c, use_container_width=True)
with t3:
    st.header("รายการสินค้า")
    st.dataframe(fetch_data("products"), use_container_width=True)
