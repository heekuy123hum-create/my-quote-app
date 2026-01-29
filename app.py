import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. การตั้งค่าหน้าตาแอป (UI CONFIG) ---
st.set_page_config(page_title="ระบบออกใบเสนอราคามาตรฐาน", layout="wide")

# ดึงค่า Config จาก Environment Variables (ใน Render)
MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่า SUPABASE_URL และ SUPABASE_KEY ในระบบให้เรียบร้อยก่อนใช้งาน")
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

# ฟังก์ชันจัดการข้อมูล
def fetch_data(table_name):
    try:
        res = conn.table(table_name).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- 2. ฟังก์ชันสร้าง PDF (เวอร์ชันแก้ทางเรื่องฟอนต์หนา) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total):
    pdf = FPDF()
    pdf.add_page()
    
    # ดึงไฟล์ฟอนต์ที่พี่อัปโหลดไว้ (THSarabunNew.ttf)
    font_path = "THSarabunNew.ttf"
    
    if os.path.exists(font_path):
        # โหลดฟอนต์ตัวธรรมดา
        pdf.add_font('THSarabun', '', font_path)
        # โหลดฟอนต์เดิมเข้าช่อง 'B' (ตัวหนา) เพื่อหลอกระบบไม่ให้พ่น Error Undefined
        # วิธีนี้จะทำให้พี่เรียกใช้ตัวหนาได้โดยไม่ต้องอัปโหลดไฟล์เพิ่ม
        pdf.add_font('THSarabun', 'B', font_path) 
        use_font = 'THSarabun'
    else:
        # กรณีฉุกเฉินหาไฟล์ไม่เจอ จะใช้ Arial แทน
        pdf.set_font("Arial", '', 14)
        use_font = 'Arial'
        st.warning("❌ คำเตือน: ไม่พบไฟล์ฟอนต์ THSarabunNew.ttf บนระบบ")

    # ส่วนหัวใบเสนอราคา - ใช้ตัวหนา (B) ได้แล้วไม่พัง
    pdf.set_font(use_font, 'B', 22)
    pdf.cell(0, 15, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')
    
    pdf.set_font(use_font, '', 15)
    pdf.cell(0, 10, f"เลขที่เอกสาร: {doc_no if doc_no else '-'}", 0, 1)
    pdf.cell(0, 10, f"วันที่ออกเอกสาร: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    # ข้อมูลลูกค้า
    pdf.set_font(use_font, 'B', 16)
    pdf.cell(0, 10, "ข้อมูลลูกค้า (Customer Information):", 0, 1)
    pdf.set_font(use_font, '', 15)
    pdf.cell(0, 10, f"ชื่อลูกค้า: {cust_name if cust_name else '-'}", 0, 1)
    pdf.multi_cell(0, 10, f"ที่อยู่: {cust_addr if cust_addr else '-'}")
    pdf.ln(10)
    
    # ส่วนหัวตารางรายการสินค้า
    pdf.set_fill_color(240, 240, 240) # สีพื้นหลังหัวตาราง
    pdf.set_font(use_font, 'B', 15)
    pdf.cell(90, 12, "รายการ (Description)", 1, 0, 'C', True)
    pdf.cell(20, 12, "จำนวน", 1, 0, 'C', True)
    pdf.cell(35, 12, "ราคา/หน่วย", 1, 0, 'C', True)
    pdf.cell(45, 12, "รวมเงิน", 1, 1, 'C', True)
    
    # รายการสินค้าจากตาราง
    pdf.set_font(use_font, '', 15)
    for _, row in df_items.iterrows():
        # ดึงข้อมูลจากแถว (ถ้าว่างให้ใส่ค่าเริ่มต้น)
        desc = str(row.get('รายการ', '-')) if row.get('รายการ') else "-"
        qty = float(row.get('จำนวน', 0))
        price = float(row.get('ราคา/หน่วย', 0))
        line_total = qty * price
        
        # พิมพ์ลง PDF (เฉพาะบรรทัดที่มีข้อมูลหรือมีการคำนวณ)
        if line_total > 0 or desc != "-":
            pdf.cell(90, 12, desc, 1)
            pdf.cell(20, 12, f"{qty:,.0f}", 1, 0, 'C')
            pdf.cell(35, 12, f"{price:,.0f}", 1, 0, 'R')
            pdf.cell(45, 12, f"{line_total:,.0f}", 1, 1, 'R')
            
    pdf.ln(5)
    
    # สรุปยอดเงินท้ายเอกสาร
    pdf.set_font(use_font, 'B', 16)
    pdf.cell(145, 10, "รวมเงินทั้งสิ้น (Subtotal):", 0, 0, 'R')
    pdf.cell(45, 10, f"{subtotal:,.0f} บาท", 0, 1, 'R')
    
    pdf.cell(145, 10, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(45, 10, f"{vat:,.0f} บาท", 0, 1, 'R')
    
    # ยอดสุทธิทำสีแดงหรือตัวใหญ่
    pdf.set_text_color(200, 0, 0)
    pdf.cell(145, 12, "ยอดรวมสุทธิ (Grand Total):", 0, 0, 'R')
    pdf.cell(45, 12, f"{grand_total:,.0f} บาท", 0, 1, 'R')
    
    # คืนค่าสีตัวหนังสือเป็นสีดำปกติ
    pdf.set_text_color(0, 0, 0)
    
    # แก้ Error: ห้ามใส่ .encode('latin-1') เพราะ fpdf2 คืนค่าเป็น bytes อยู่แล้ว
    return pdf.output()

# --- 3. หน้าจอแอปพลิเคชัน (MAIN UI) ---
st.title("📄 ระบบจัดการใบเสนอราคา (Full Edition)")

tab_doc, tab_cust, tab_prod = st.tabs(["📝 สร้างเอกสารใหม่", "👥 ฐานข้อมูลลูกค้า", "📦 คลังสินค้า"])

with tab_doc:
    # ดึงข้อมูลมาเตรียมไว้
    df_customers = fetch_data("customers")
    df_products = fetch_data("products")

    col_1, col_2, col_3 = st.columns([1.5, 2, 1.5])
    
    with col_1:
        st.subheader("ข้อมูลลูกค้า")
        # ใช้คอลัมน์แรกสุดเป็นตัวเลือกหลัก เพื่อเลี่ยงปัญหาชื่อ ID ไม่ตรง
        c_list = ["-- เลือกรายชื่อ --"]
        if not df_customers.empty:
            c_list += df_customers.iloc[:, 0].tolist()
            
        select_id = st.selectbox("รหัสลูกค้า", options=c_list)
        
        # ดึงข้อมูลมาลงช่องกรอกอัตโนมัติ
        c_info = {}
        if select_id != "-- เลือกรายชื่อ --" and not df_customers.empty:
            c_info = df_customers[df_customers.iloc[:, 0] == select_id].iloc[0].to_dict()
            
        c_name = st.text_input("ชื่อลูกค้า/บริษัท", value=c_info.get('name', ''))
        c_phone = st.text_input("เบอร์โทรศัพท์", value=c_info.get('phone', ''))

    with col_2:
        st.subheader("ที่อยู่จัดส่ง")
        c_addr = st.text_area("ที่อยู่โดยละเอียด", value=c_info.get('address', ''), height=122)

    with col_3:
        st.subheader("ข้อมูลเอกสาร")
        doc_id = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d-%H%M')}")
        vat_toggle = st.checkbox("คิดภาษีมูลค่าเพิ่ม 7%", value=True)

    st.divider()

    # ส่วนตารางสินค้า (Dynamic Data Editor)
    st.subheader("รายการสินค้าและบริการ")
    # สร้างค่าเริ่มต้น 8 แถว
    grid_init = [{"รายการ": "", "จำนวน": 0, "ราคา/หน่วย": 0}] * 8
    edited_grid = st.data_editor(grid_init, num_rows="dynamic", use_container_width=True)

    # คำนวณเงินแบบ Real-time
    df_calc = pd.DataFrame(edited_grid)
    df_calc['line_total'] = pd.to_numeric(df_calc['จำนวน'], errors='coerce').fillna(0) * \
                            pd.to_numeric(df_calc['ราคา/หน่วย'], errors='coerce').fillna(0)
    
    sub_total_amt = int(round(df_calc['line_total'].sum()))
    vat_amt = int(round(sub_total_amt * 0.07)) if vat_toggle else 0
    grand_total_amt = sub_total_amt + vat_amt

    st.divider()
    
    # สรุปผลลัพธ์และปุ่มดาวน์โหลด
    col_sum1, col_sum2 = st.columns([2.5, 1])
    with col_sum2:
        st.write(f"ยอดรวมก่อนภาษี: **{sub_total_amt:,}** บาท")
        st.write(f"ภาษีมูลค่าเพิ่ม (7%): **{vat_amt:,}** บาท")
        st.markdown(f"### **ยอดสุทธิ: {grand_total_amt:,} บาท**")
        
        if st.button("บันทึกข้อมูลและเตรียมไฟล์ PDF", type="primary"):
            try:
                # สร้าง PDF ทันที
                pdf_bytes = create_pdf(doc_id, c_name, c_addr, df_calc, sub_total_amt, vat_amt, grand_total_amt)
                
                # แสดงปุ่มดาวน์โหลดจริง
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ PDF",
                    data=pdf_bytes,
                    file_name=f"{doc_id}.pdf",
                    mime="application/pdf"
                )
                st.success("สร้างเอกสารสำเร็จ! กรุณากดปุ่มดาวน์โหลดด้านบน")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสร้าง PDF: {e}")

# TAB จัดการฐานข้อมูล (คงไว้ครบถ้วน)
with tab_cust:
    st.header("👥 รายชื่อลูกค้า")
    st.dataframe(df_customers, use_container_width=True)

with tab_prod:
    st.header("📦 รายการสินค้าในคลัง")
    st.dataframe(df_products, use_container_width=True)
