import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & DB CONNECTION ---
st.set_page_config(page_title="ระบบออกใบเสนอราคา (Full Design)", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่า Environment Variables: SUPABASE_URL และ SUPABASE_KEY ใน Render")
    st.stop()

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"เชื่อมต่อฐานข้อมูลล้มเหลว: {e}")
    st.stop()

def fetch_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 2. ฟังก์ชันค้นหาโลโก้ใน GitHub อัตโนมัติ ---
def find_logo():
    # ตรวจสอบไฟล์นามสกุลยอดนิยม
    for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG']:
        filename = f"logo.{ext}"
        if os.path.exists(filename):
            return filename
    return None

# --- 3. ฟังก์ชันสร้าง PDF (ดีไซน์เต็มรูปแบบ 20 แถว) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total, sig_names):
    pdf = FPDF()
    pdf.add_page()
    
    # การจัดการฟอนต์ภาษาไทย
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_font = 'THSarabun'
    else:
        pdf.set_font("Arial", '', 14)
        use_font = 'Arial'

    # --- ใส่โลโก้มุมซ้ายบน (ถ้ามีไฟล์ชื่อ logo อยู่ในระบบ) ---
    logo_path = find_logo()
    if logo_path:
        pdf.image(logo_path, x=10, y=10, w=35)
        pdf.set_y(35) 
    else:
        pdf.set_y(20)

    # หัวเอกสาร (ชิดขวาถ้ามีโลโก้)
    pdf.set_font(use_font, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R' if logo_path else 'C')
    pdf.ln(5)

    # ข้อมูลลูกค้า และเลขที่เอกสาร
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(120, 8, "ข้อมูลลูกค้า (Customer Details):", 0, 0)
    pdf.cell(70, 8, f"เลขที่: {doc_no}", 0, 1, 'R')

    pdf.set_font(use_font, '', 14)
    pdf.cell(120, 8, f"ชื่อ: {cust_name if cust_name else ''}", 0, 0)
    pdf.cell(70, 8, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.multi_cell(0, 8, f"ที่อยู่: {cust_addr if cust_addr else ''}")
    pdf.ln(5)

    # --- ตารางรายการสินค้า (20 แถวเต็มหน้า) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_font, 'B', 12)
    h = 9 # ความสูงแถว
    
    # หัวตาราง (อิงตามไฟล์เก่าของพี่)
    pdf.cell(10, h, "ลำดับ", 1, 0, 'C', True)
    pdf.cell(25, h, "รหัสสินค้า", 1, 0, 'C', True)
    pdf.cell(60, h, "รายการสินค้า", 1, 0, 'C', True)
    pdf.cell(15, h, "จำนวน", 1, 0, 'C', True)
    pdf.cell(15, h, "หน่วย", 1, 0, 'C', True)
    pdf.cell(25, h, "ราคา/หน่วย", 1, 0, 'C', True)
    pdf.cell(40, h, "รวมเงิน", 1, 1, 'C', True)

    pdf.set_font(use_font, '', 13)
    
    # วนลูปสร้างให้ครบ 20 แถว
    for i in range(20):
        if i < len(df_items):
            row = df_items.iloc[i]
            # แสดงค่าว่างแทนที่ 0 หรือขีด
            d_no = str(i + 1)
            d_code = str(row.get('รหัสสินค้า', ''))
            d_desc = str(row.get('รายการ', ''))
            d_qty = f"{float(row.get('จำนวน', 0)):,.0f}" if float(row.get('จำนวน', 0)) > 0 else ""
            d_unit = str(row.get('หน่วย', ''))
            d_price = f"{float(row.get('ราคา/หน่วย', 0)):,.0f}" if float(row.get('ราคา/หน่วย', 0)) > 0 else ""
            d_total = f"{float(row.get('รวมเงิน', 0)):,.0f}" if float(row.get('รวมเงิน', 0)) > 0 else ""
        else:
            d_no, d_code, d_desc, d_qty, d_unit, d_price, d_total = "", "", "", "", "", "", ""

        pdf.cell(10, h, d_no, 1, 0, 'C')
        pdf.cell(25, h, d_code, 1, 0, 'C')
        pdf.cell(60, h, d_desc, 1, 0, 'L')
        pdf.cell(15, h, d_qty, 1, 0, 'C')
        pdf.cell(15, h, d_unit, 1, 0, 'C')
        pdf.cell(25, h, d_price, 1, 0, 'R')
        pdf.cell(40, h, d_total, 1, 1, 'R')

    # สรุปยอดเงิน
    pdf.ln(3)
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(150, 8, "รวมเงิน (Sub Total):", 0, 0, 'R')
    pdf.cell(40, 8, f"{subtotal:,.0f} บาท", 'B', 1, 'R')
    pdf.cell(150, 8, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(40, 8, f"{vat:,.0f} บาท", 'B', 1, 'R')
    pdf.set_font(use_font, 'B', 16)
    pdf.cell(150, 10, "ยอดรวมสุทธิ (Grand Total):", 0, 0, 'R')
    pdf.set_text_color(200, 0, 0)
    pdf.cell(40, 10, f"{grand_total:,.0f} บาท", 'B', 1, 'R')
    pdf.set_text_color(0, 0, 0)

    # พื้นที่เซ็นชื่อ (3 ช่อง)
    pdf.ln(10)
    sig_y = pdf.get_y()
    pdf.set_font(use_font, '', 12)
    # ช่อง 1
    pdf.set_xy(10, sig_y)
    pdf.cell(60, 6, "..........................................", 0, 1, 'C')
    pdf.cell(60, 6, "ผู้อนุมัติสั่งซื้อ", 0, 1, 'C')
    pdf.cell(60, 6, f"({sig_names[0]})", 0, 1, 'C')
    # ช่อง 2
    pdf.set_xy(75, sig_y)
    pdf.cell(60, 6, "..........................................", 0, 1, 'C')
    pdf.cell(60, 6, "พนักงานขาย", 0, 1, 'C')
    pdf.cell(60, 6, f"({sig_names[1]})", 0, 1, 'C')
    # ช่อง 3
    pdf.set_xy(140, sig_y)
    pdf.cell(60, 6, "..........................................", 0, 1, 'C')
    pdf.cell(60, 6, "ผู้จัดการฝ่ายขาย", 0, 1, 'C')
    pdf.cell(60, 6, f"({sig_names[2]})", 0, 1, 'C')

    return bytes(pdf.output())

# --- 4. STREAMLIT UI ---
st.title("📄 ระบบจัดการใบเสนอราคา (Full Version)")

# Sidebar ตรวจสอบโลโก้
logo_file = find_logo()
if logo_file:
    st.sidebar.success(f"✅ พบโลโก้: {logo_file}")
    st.sidebar.image(logo_file, width=150)
else:
    st.sidebar.warning("❌ ไม่พบไฟล์โลโก้ใน GitHub (ตั้งชื่อ logo.png หรือ logo.jpg)")

tab1, tab2, tab3 = st.tabs(["📝 สร้างเอกสาร", "👥 ลูกค้า", "📦 สินค้า"])

with tab1:
    df_c = fetch_data("customers")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("ข้อมูลลูกค้า")
        c_list = ["-- เลือก --"] + (df_c.iloc[:, 0].tolist() if not df_c.empty else [])
        sid = st.selectbox("เลือกรหัสลูกค้า", options=c_list)
        info = df_c[df_c.iloc[:, 0] == sid].iloc[0] if sid != "-- เลือก --" else {}
        name = st.text_input("ชื่อลูกค้า", value=info.get('name', ''))
        addr = st.text_area("ที่อยู่จัดส่ง", value=info.get('address', ''), height=100)

    with col2:
        st.subheader("ตั้งค่าเอกสาร")
        dno = st.text_input("เลขที่เอกสาร", f"QT-{datetime.now().strftime('%Y%m%d-%H')}")
        v_on = st.checkbox("VAT 7%", value=True)
        sig1 = st.text_input("ชื่อผู้อนุมัติ", "................................")
        sig2 = st.text_input("ชื่อพนักงานขาย", "................................")
        sig3 = st.text_input("ชื่อผู้จัดการ", "................................")

    st.divider()
    
    st.subheader("รายการสินค้า (ตีเส้น 20 แถวใน PDF)")
    grid_init = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา/หน่วย": 0}] * 20
    edited_data = st.data_editor(grid_init, num_rows="dynamic", use_container_width=True, height=500)

    # คำนวณเงิน
    df_res = pd.DataFrame(edited_data)
    df_res['รวมเงิน'] = pd.to_numeric(df_res['จำนวน'], 0) * pd.to_numeric(df_res['ราคา/หน่วย'], 0)
    
    sub = int(round(df_res['รวมเงิน'].sum()))
    v_val = int(round(sub * 0.07)) if v_on else 0
    grand = sub + v_val

    st.divider()
    if st.button("บันทึกและสร้างไฟล์ PDF", type="primary"):
        try:
            pdf_out = create_pdf(dno, name, addr, df_res, sub, v_val, grand, [sig1, sig2, sig3])
            st.download_button("📥 ดาวน์โหลดใบเสนอราคา", data=pdf_out, file_name=f"{dno}.pdf", mime="application/pdf")
            st.success("สร้างไฟล์สำเร็จ!")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# TAB อื่นๆ
with tab2: st.dataframe(df_c, use_container_width=True)
with tab3: st.dataframe(fetch_data("products"), use_container_width=True)
