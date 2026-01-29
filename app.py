import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
import io # เพิ่ม library สำหรับจัดการไฟล์รูปภาพ
from fpdf import FPDF

# --- 1. SETUP ---
st.set_page_config(page_title="ระบบออกใบเสนอราคา Pro", layout="wide")

MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("กรุณาตั้งค่า Environment Variables ใน Render")
    st.stop()

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=MY_SUPABASE_URL, key=MY_SUPABASE_KEY)
except Exception as e:
    st.error(f"เชื่อมต่อฐานข้อมูลไม่ได้: {e}")
    st.stop()

def fetch_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 2. PDF FUNCTION (อัปเกรดใหม่) ---
def create_pdf(doc_no, cust_name, cust_addr, df_items, subtotal, vat, grand_total, logo_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    
    # --- ส่วนจัดการฟอนต์ (เหมือนเดิม) ---
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path) 
        use_font = 'THSarabun'
    else:
        pdf.set_font("Arial", '', 14)
        use_font = 'Arial'
        st.error("❌ ไม่พบไฟล์ฟอนต์ THSarabunNew.ttf")

    # --- 1. ใส่โลโก้มุมซ้ายบน (ถ้ามีอัปโหลดมา) ---
    if logo_bytes:
        # แปลงข้อมูล bytes ของรูปภาพให้ fpdf อ่านได้
        image_stream = io.BytesIO(logo_bytes.getvalue())
        # วางรูปที่ตำแหน่ง x=10, y=10, กำหนดความกว้าง 30mm (ปรับได้)
        pdf.image(image_stream, x=10, y=10, w=30)
        # ขยับเคอร์เซอร์ลงมาข้างล่างโลโก้
        pdf.set_y(35) 
    else:
        # ถ้าไม่มีโลโก้ ก็เริ่มบรรทัดปกติ
        pdf.set_y(20)

    # --- ส่วนหัวเอกสาร ---
    pdf.set_font(use_font, 'B', 24)
    # ปรับตำแหน่งชื่อเอกสารให้ไปอยู่กึ่งกลางค่อนขวา ถ้ามีโลโก้
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'R' if logo_bytes else 'C')
    pdf.ln(5)

    # --- ข้อมูลลูกค้าและเลขที่ ---
    pdf.set_font(use_font, 'B', 14)
    # ข้อมูลลูกค้า (ซ้าย)
    pdf.cell(120, 8, "ข้อมูลลูกค้า (Customer Details):", 0, 0)
    # เลขที่เอกสาร (ขวา)
    pdf.cell(70, 8, f"เลขที่: {doc_no}", 0, 1, 'R')

    pdf.set_font(use_font, '', 14)
    # ชื่อลูกค้า (ซ้าย)
    pdf.cell(120, 8, f"ชื่อ: {cust_name if cust_name else ''}", 0, 0) # ถ้าว่างให้เป็นค่าว่าง ""
    # วันที่ (ขวา)
    pdf.cell(70, 8, f"วันที่: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')

    # ที่อยู่ (เต็มบรรทัด)
    pdf.multi_cell(0, 8, f"ที่อยู่: {cust_addr if cust_addr else ''}")
    pdf.ln(5)
    
    # --- ตารางรายการ (แบบเต็มหน้ากระดาษ) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_font, 'B', 14)
    row_height = 10 # ความสูงของแต่ละแถว

    # หัวตาราง
    pdf.cell(90, row_height, "รายการ (Description)", 1, 0, 'C', True)
    pdf.cell(20, row_height, "จำนวน", 1, 0, 'C', True)
    pdf.cell(35, row_height, "ราคา/หน่วย", 1, 0, 'C', True)
    pdf.cell(45, row_height, "รวมเงิน", 1, 1, 'C', True)
    
    pdf.set_font(use_font, '', 14)
    
    # *** จุดสำคัญ: วนลูปสร้างตารางให้ครบ 20 บรรทัดเสมอ ***
    TARGET_ROWS = 20 # อยากได้กี่บรรทัดแก้ตรงนี้
    
    for i in range(TARGET_ROWS):
        # ตรวจสอบว่ามีข้อมูลใน DataFrame ถึง index นี้หรือไม่
        if i < len(df_items):
            row = df_items.iloc[i]
            # ดึงค่า ถ้าไม่มีให้เป็นค่าว่าง "" (ไม่ใช่ "-")
            name = str(row.get('รายการ', ''))
            qty = float(row.get('จำนวน', 0))
            price = float(row.get('ราคา/หน่วย', 0))
            total = qty * price

            # แปลงเป็นข้อความ ถ้าเป็น 0 หรือว่าง ให้เป็นช่องว่างๆ
            name_str = name if name else ""
            qty_str = f"{qty:,.0f}" if qty > 0 else ""
            price_str = f"{price:,.0f}" if price > 0 else ""
            total_str = f"{total:,.0f}" if total > 0 else ""
        else:
            # ถ้าเกินจำนวนข้อมูลที่มี ให้ตีเส้นเปล่าๆ
            name_str, qty_str, price_str, total_str = "", "", "", ""

        # พิมพ์แถว (ตีเส้นกรอบทุกครั้งแม้ไม่มีข้อมูล)
        pdf.cell(90, row_height, name_str, 1)
        pdf.cell(20, row_height, qty_str, 1, 0, 'C')
        pdf.cell(35, row_height, price_str, 1, 0, 'R')
        pdf.cell(45, row_height, total_str, 1, 1, 'R')
            
    pdf.ln(5)
    
    # --- สรุปยอดเงิน ---
    pdf.set_font(use_font, 'B', 14)
    pdf.cell(145, 10, "รวมเงิน (Subtotal):", 0, 0, 'R')
    pdf.cell(45, 10, f"{subtotal:,.0f} บาท", 0, 1, 'R')
    
    pdf.cell(145, 10, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(45, 10, f"{vat:,.0f} บาท", 0, 1, 'R')
    
    # เส้นคั่นยอดสุทธิ
    pdf.set_draw_color(100, 100, 100)
    pdf.line(155, pdf.get_y(), 200, pdf.get_y())
    
    pdf.set_font(use_font, 'B', 18)
    pdf.cell(145, 14, "ยอดสุทธิ (Grand Total):", 0, 0, 'R')
    pdf.cell(45, 14, f"{grand_total:,.0f} บาท", 0, 1, 'R')
    
    # เส้นปิดท้ายสองเส้น
    y_final = pdf.get_y()
    pdf.line(155, y_final, 200, y_final)
    pdf.line(155, y_final+1, 200, y_final+1)

    # --- พื้นที่เซ็นชื่อ ---
    pdf.set_y(-40) # ขยับไปที่ 4 ซม. จากท้ายกระดาษ
    pdf.set_font(use_font, '', 14)
    pdf.cell(100, 10, "ลงชื่อ .................................................... ผู้เสนอราคา", 0, 0, 'C')
    pdf.cell(100, 10, "ลงชื่อ .................................................... ผู้อนุมัติ", 0, 1, 'C')
    
    # คืนค่าเป็น bytes (สำคัญมาก ห้ามลบ .encode ออก)
    return bytes(pdf.output())

# --- 3. UI ---
st.title("📄 ระบบออกใบเสนอราคา (Pro Version)")

t1, t2, t3 = st.tabs(["📝 สร้างเอกสาร", "👥 ลูกค้า", "📦 สินค้า"])

with t1:
    # --- ส่วนอัปโหลดโลโก้ ---
    with st.expander("🖼️ ตั้งค่าโลโก้บริษัท (คลิกเพื่อเปิด)", expanded=False):
        uploaded_logo = st.file_uploader("อัปโหลดไฟล์รูปภาพโลโก้ (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        if uploaded_logo:
            st.image(uploaded_logo, width=100, caption="ตัวอย่างโลโก้")

    st.divider()

    df_c = fetch_data("customers")
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    
    with col1:
        st.subheader("ลูกค้า")
        c_list = ["-- เลือก --"] + (df_c.iloc[:, 0].tolist() if not df_c.empty else [])
        sid = st.selectbox("เลือกรหัส", options=c_list)
        info = df_c[df_c.iloc[:, 0] == sid].iloc[0] if sid != "-- เลือก --" else {}
        name = st.text_input("ชื่อ", value=info.get('name', ''))

    with col2:
        st.subheader("ที่อยู่")
        addr = st.text_area("ที่อยู่จัดส่ง", value=info.get('address', ''), height=122)

    with col3:
        st.subheader("เอกสาร")
        dno = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%Y%m%d-%H')}")
        vat_on = st.checkbox("VAT 7%", value=True)

    st.divider()
    
    st.subheader("รายการสินค้า")
    # เพิ่มจำนวนบรรทัดเริ่มต้นในหน้าเว็บให้เยอะขึ้น (20 บรรทัด)
    grid_rows = [{"รายการ": "", "จำนวน": 0, "ราคา/หน่วย": 0}] * 20
    # ใช้ data_editor แบบให้เพิ่มลดแถวได้
    edited_grid = st.data_editor(grid_rows, num_rows="dynamic", use_container_width=True, height=600)

    # คำนวณเงิน (เฉพาะแถวที่มีข้อมูล)
    df_res = pd.DataFrame(edited_grid)
    # กรองแถวที่ว่างเปล่าทิ้งก่อนคำนวณ (แถวที่ไม่มีชื่อรายการ และ ยอดเป็น 0)
    df_calc = df_res[~((df_res['รายการ'] == "") & (df_res['จำนวน'] == 0) & (df_res['ราคา/หน่วย'] == 0))].copy()

    df_calc['total'] = pd.to_numeric(df_calc['จำนวน'], errors='coerce').fillna(0) * \
                       pd.to_numeric(df_calc['ราคา/หน่วย'], errors='coerce').fillna(0)
    
    sub = int(round(df_calc['total'].sum()))
    v_val = int(round(sub * 0.07)) if vat_on else 0
    grand = sub + v_val

    st.divider()
    c_sum1, c_sum2 = st.columns([3, 1])
    with c_sum2:
        st.markdown(f"### **ยอดสุทธิ: {grand:,} บาท**")
        
        if st.button("บันทึกและดาวน์โหลด PDF", type="primary"):
            try:
                # ส่งไฟล์โลโก้ที่อัปโหลดไปด้วย (ถ้ามี)
                pdf_data = create_pdf(dno, name, addr, df_calc, sub, v_val, grand, logo_bytes=uploaded_logo)
                st.download_button("📥 โหลด PDF", data=pdf_data, file_name=f"{dno}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Error: {e}")

# TAB อื่นๆ
with t2:
    st.header("จัดการลูกค้า")
    st.dataframe(df_c, use_container_width=True)
with t3:
    st.header("จัดการสินค้า")
    st.dataframe(fetch_data("products"), use_container_width=True)
