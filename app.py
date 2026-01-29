import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & DB ---
st.set_page_config(page_title="ระบบออกใบเสนอราคา (A4 Perfect)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่าความปลอดภัยก่อนใช้งาน")
    st.stop()

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"เชื่อมต่อฐานข้อมูลล้มเหลว: {e}")
    st.stop()

# --- 2. LOGO AUTO-DETECT ---
def get_logo():
    for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG']:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. PDF ENGINE (โครงสร้าง A4 ตามต้นฉบับ Chrome) ---
def create_pdf(doc_no, c_name, c_addr, df_items, subtotal, vat, grand_total, sigs):
    # ตั้งค่าขอบกระดาษให้แคบลง (L: 10, T: 10, R: 10)
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else:
        pdf.set_font("Arial", '', 14)
        use_f = 'Arial'

    # --- ส่วนหัว (Header Area) ---
    logo = get_logo()
    if logo:
        pdf.image(logo, x=10, y=10, w=35)
        pdf.set_y(15)
    else:
        pdf.set_y(10)

    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R')
    pdf.ln(5)

    # ข้อมูลลูกค้า (แบ่งซ้าย-ขวา)
    pdf.set_font(use_f, 'B', 14)
    curr_y = pdf.get_y()
    pdf.cell(120, 7, "ข้อมูลลูกค้า (Customer Details):", 0, 0)
    pdf.cell(0, 7, f"เลขที่เอกสาร: {doc_no}", 0, 1, 'R')

    pdf.set_font(use_f, '', 14)
    pdf.cell(120, 7, f"ชื่อลูกค้า: {c_name if c_name else ''}", 0, 0)
    pdf.cell(0, 7, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 7, f"ที่อยู่: {c_addr if c_addr else ''}")
    pdf.ln(2)

    # --- ตารางรายการ (20 แถวเต็มหน้า) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 12)
    h = 8.5 # ปรับความสูงแถวให้พอดี A4
    
    # ความกว้างคอลัมน์รวม 190mm พอดีขอบ
    # ลำดับ(10), รหัส(25), รายการ(70), จำนวน(15), หน่วย(15), ราคา(25), รวม(30)
    w = [10, 25, 70, 15, 15, 25, 30] 
    headers = ["ลำดับ", "รหัสสินค้า", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "รวมเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], h, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 13)
    for i in range(20):
        if i < len(df_items):
            row = df_items.iloc[i]
            # กรองข้อมูล: ไม่ใส่ 0 ไม่ใส่ขีด ถ้าไม่มีคือว่าง
            qty_val = float(row.get('qty_num', 0))
            price_val = float(row.get('price_num', 0))
            total_val = float(row.get('รวมเงิน', 0))

            d = [
                str(i + 1),
                str(row.get('รหัสสินค้า', '') or ''),
                str(row.get('รายการ', '') or ''),
                f"{qty_val:,.0f}" if qty_val > 0 else "",
                str(row.get('หน่วย', '') or ''),
                f"{price_val:,.0f}" if price_val > 0 else "",
                f"{total_val:,.0f}" if total_val > 0 else ""
            ]
        else:
            d = ["", "", "", "", "", "", ""]

        for j in range(len(d)):
            align = 'C' if j in [0, 1, 3, 4] else ('L' if j == 2 else 'R')
            pdf.cell(w[j], h, d[j], 1, 0, align)
        pdf.ln()

    # --- ส่วนสรุปเงิน (Summary) ---
    pdf.ln(2)
    pdf.set_font(use_f, 'B', 14)
    # ขยับไปชิดขวา
    pdf.set_x(130)
    pdf.cell(40, 8, "รวมเงิน (Sub Total):", 0, 0, 'R')
    pdf.cell(30, 8, f"{subtotal:,.0f}", 'B', 1, 'R')
    
    pdf.set_x(130)
    pdf.cell(40, 8, "ภาษี (VAT 7%):", 0, 0, 'R')
    pdf.cell(30, 8, f"{vat:,.0f}", 'B', 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font(use_f, 'B', 16)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(40, 10, "ยอดรวมสุทธิ:", 0, 0, 'R')
    pdf.cell(30, 10, f"{grand_total:,.0f}", 'B', 1, 'R')
    pdf.set_text_color(0, 0, 0)

    # --- ส่วนลงนาม (Footer Area - Fixed Bottom) ---
    # บังคับพิกัด Y จากท้ายกระดาษขึ้นมา 55mm (เหมือน absolute bottom ใน Chrome)
    pdf.set_y(-55)
    pdf.set_font(use_f, '', 12)
    labels = ["ผู้อนุมัติสั่งซื้อ", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    
    # คำนวณตำแหน่ง X ให้กระจายตัวสวยๆ
    start_x = 10
    box_w = 60
    for i in range(3):
        pdf.set_xy(start_x + (i * 65), pdf.get_y())
        pdf.cell(box_w, 5, "...................................................", 0, 1, 'C')
        pdf.set_x(start_x + (i * 65))
        pdf.cell(box_w, 5, labels[i], 0, 1, 'C')
        pdf.set_x(start_x + (i * 65))
        pdf.cell(box_w, 5, f"({sigs[i]})", 0, 1, 'C')
        pdf.set_y(pdf.get_y() - 15) # ดึง Y กลับขึ้นไปสำหรับลูปถัดไป

    return bytes(pdf.output())

# --- 4. STREAMLIT UI ---
st.title("📄 ระบบใบเสนอราคา (Official A4 Format)")

tab1, tab2, tab3 = st.tabs(["📝 สร้างเอกสาร", "👥 ข้อมูลลูกค้า", "📦 คลังสินค้า"])

with tab1:
    # ดึงข้อมูลลูกค้า
    res_c = conn.table("customers").select("*").execute()
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("ส่วนที่ 1: รายละเอียดลูกค้า")
        c_list = ["-- เลือก --"] + (df_c.iloc[:, 0].tolist() if not df_c.empty else [])
        sid = st.selectbox("เลือกลูกค้า", options=c_list)
        info = df_c[df_c.iloc[:, 0] == sid].iloc[0] if sid != "-- เลือก --" else {}
        name = st.text_input("ชื่อบริษัท/ลูกค้า", value=info.get('name', ''))
        addr = st.text_area("ที่อยู่", value=info.get('address', ''), height=100)

    with c2:
        st.subheader("ส่วนที่ 2: ผู้ออกเอกสาร")
        dno = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        v_on = st.checkbox("คิดภาษี VAT 7%", value=True)
        s1 = st.text_input("ชื่อผู้อนุมัติ (ลูกค้า)", "....................")
        s2 = st.text_input("ชื่อพนักงานขาย", "....................")
        s3 = st.text_input("ชื่อผู้จัดการ", "....................")

    st.divider()
    
    # ตาราง 20 แถว
    st.subheader("ส่วนที่ 3: รายการสินค้า")
    grid_init = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0}] * 20
    edited = st.data_editor(grid_init, num_rows="dynamic", use_container_width=True)
    
    # ✅ แก้ไข ValueError: ปรับการคำนวณใหม่ให้ปลอดภัย
    df_grid = pd.DataFrame(edited)
    # แปลงเป็นตัวเลข ถ้าพังให้เป็น 0
    df_grid['qty_num'] = pd.to_numeric(df_grid['จำนวน'], errors='coerce').fillna(0)
    df_grid['price_num'] = pd.to_numeric(df_grid['ราคา'], errors='coerce').fillna(0)
    df_grid['รวมเงิน'] = df_grid['qty_num'] * df_grid['price_num']
    
    sub = int(df_grid['รวมเงิน'].sum())
    v_amt = int(sub * 0.07) if v_on else 0
    grand = sub + v_amt

    if st.button("🔥 บันทึกและสร้าง PDF (A4 Full)", type="primary"):
        try:
            pdf_out = create_pdf(dno, name, addr, df_grid, sub, v_amt, grand, [s1, s2, s3])
            st.download_button("📥 ดาวน์โหลดไฟล์ใบเสนอราคา", data=pdf_out, file_name=f"{dno}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการสร้างไฟล์: {e}")

# TAB อื่นๆ แสดงดาต้าเบสปกติ
with tab2: st.dataframe(df_c, use_container_width=True)
with tab3: st.dataframe(pd.DataFrame(conn.table("products").select("*").execute().data), use_container_width=True)
