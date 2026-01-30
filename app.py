import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG ---
st.set_page_config(page_title="ระบบใบเสนอราคา (Full Version)", layout="wide")

try:
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=os.environ.get("SUPABASE_URL"), 
                         key=os.environ.get("SUPABASE_KEY"))
except:
    st.error("เชื่อมต่อ Database ไม่ได้")
    st.stop()

def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val else 0.0
    except: return 0.0

# --- 2. PDF ENGINE (จัดตามฟอร์ม 595.pdf เป๊ะๆ) ---
def create_pdf(d, items_df, summary, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    use_f = 'THSarabun' if os.path.exists(font_path) else 'Arial'
    if use_f == 'THSarabun':
        pdf.add_font('THSarabun', '', font_path); pdf.add_font('THSarabun', 'B', font_path)

    # --- ส่วนหัว: โลโก้ (ซ้าย) + ข้อมูลบริษัทเรา (ถัดมาทางซ้าย) ---
    logo_path = "logo.png" # ตรวจสอบว่ามีไฟล์ logo.png ในโฟลเดอร์
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=20)
    
    pdf.set_xy(32, 10) # ขยับมาต่อจากโลโก้
    pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(100, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # --- ส่วนหัวขวา: เลขที่ และ วันที่ (ในช่องสี่เหลี่ยมตามต้นฉบับ) ---
    pdf.set_xy(140, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.multi_cell(60, 7, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}\nวันที่กำหนดส่ง: {d['due_date']}\nเครดิต: {d['credit']} วัน\nราคาเสนอถึงวันที่: {d['exp_date']}", 1, 'L')

    pdf.set_y(45); pdf.set_font(use_f, 'B', 22); pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # --- ข้อมูลลูกค้า ---
    pdf.set_font(use_f, '', 14); pdf.ln(2); curr_y = pdf.get_y()
    pdf.set_xy(10, curr_y)
    pdf.multi_cell(120, 6, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}\nเลขผู้เสียภาษี: {d['c_tax']}")

    # --- ตารางสินค้า (บังคับ 20 บรรทัดตามต้นฉบับ) ---
    pdf.set_y(curr_y + 35)
    pdf.set_fill_color(240, 240, 240); pdf.set_font(use_f, 'B', 10)
    w = [15, 70, 15, 15, 25, 20, 30] # รหัส, รายการ, จำนวน, หน่วย, ราคา, ส่วนลด, รวมเงิน
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จํานวนเงิน"]
    for i in range(len(headers)): pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 10)
    for i in range(20): # บังคับ 20 บรรทัด
        if i < len(items_df):
            row = items_df.iloc[i]
            # กรองเฉพาะแถวที่มีชื่อรายการจริง
            if str(row.get('รายการ','')).strip() != "":
                val = [str(row.get('รหัสสินค้า','')), str(row.get('รายการ','')), f"{to_num(row.get('จำนวน')):,.0f}", 
                       str(row.get('หน่วย','')), f"{to_num(row.get('ราคา')):,.0f}", f"{to_num(row.get('ส่วนลด')):,.0f}", f"{to_num(row.get('รวมเงิน')):,.0f}"]
            else: val = [""]*7
        else: val = [""]*7
        for j in range(7): pdf.cell(w[j], 6, val[j], 1, 0, 'C' if j != 1 else 'L')
        pdf.ln()

    # --- ยอดสรุปเงิน ---
    pdf.ln(1); pdf.set_font(use_f, 'B', 12)
    pdf.cell(sum(w[:-1]), 6, "รวมเงินย่อย:", 0, 0, 'R'); pdf.cell(w[-1], 6, f"{summary['subtotal']:,.0f}", 'B', 1, 'R')
    pdf.cell(sum(w[:-1]), 6, "ภาษี (7%):", 0, 0, 'R'); pdf.cell(w[-1], 6, f"{summary['vat']:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 14); pdf.set_text_color(200, 0, 0)
    pdf.cell(sum(w[:-1]), 8, "ยอดรวมทั้งสิ้น:", 0, 0, 'R'); pdf.cell(w[-1], 8, f"{summary['grand_total']:,.0f}", 'B', 1, 'R')

    # --- ลายเซ็น (3 อันเรียงหน้ากระดาน ชิดขอบล่าง) ---
    pdf.set_y(-35) 
    pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 11)
    titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    pos_x = [10, 75, 140]
    y_sig = pdf.get_y()
    
    for i in range(3):
        pdf.set_xy(pos_x[i], y_sig)
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_x(pos_x[i]); pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.set_x(pos_x[i]); pdf.cell(60, 5, names[i] if names[i] else " ", 0, 1, 'C')
        pdf.set_x(pos_x[i]); pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')

    return bytes(pdf.output())

# --- 3. UI (จัดช่องกรอกให้ครบ) ---
tab1, tab2, tab3 = st.tabs(["📝 ออกใบเสนอราคา", "👥 ลูกค้า", "📦 สินค้า"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัทเรา", "SIWAKIT")
        my_addr = st.text_input("ที่อยู่เรา")
        my_tel = st.text_input("โทรศัพท์")
        my_fax = st.text_input("โทรสาร")
        my_tax = st.text_input("เลขผู้เสียภาษี")
    with c2:
        st.subheader("📄 ข้อมูลเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        doc_date = st.text_input("วันที่เอกสาร", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("วันที่กำหนดส่ง", "7 วัน")
        exp_date = st.text_input("ยืนราคาถึงวันที่", "30 วัน")
        credit = st.number_input("เครดิต (วัน)", 0)

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("👤 ข้อมูลลูกค้า")
        c_name = st.text_input("บริษัทลูกค้า")
        contact = st.text_input("ชื่อผู้ติดต่อ")
        c_addr = st.text_area("ที่อยู่ลูกค้า", height=65)
    with c4:
        st.write("<br><br>", unsafe_allow_html=True)
        c_tel = st.text_input("โทรลูกค้า")
        c_fax = st.text_input("โทรสารลูกค้า")
        c_tax = st.text_input("เลขผู้เสียภาษีลูกค้า")

    st.divider()
    # ตาราง 20 แถว
    grid = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 20, 
                          num_rows="dynamic", use_container_width=True)
    
    df_grid = pd.DataFrame(grid)
    df_grid['qty_num'] = df_grid['จำนวน'].apply(to_num)
    df_grid['price_num'] = df_grid['ราคา'].apply(to_num)
    df_grid['discount_num'] = df_grid['ส่วนลด'].apply(to_num)
    df_grid['รวมเงิน'] = (df_grid['qty_num'] * df_grid['price_num']) - df_grid['discount_num']
    
    sub = df_grid['รวมเงิน'].sum(); vat = sub * 0.07; grand = sub + vat

    st.subheader("✍️ ผู้ลงนาม")
    sc1, sc2, sc3 = st.columns(3)
    s1 = sc1.text_input("ชื่อผู้อนุมัติซื้อ", "")
    s2 = sc2.text_input("ชื่อพนักงานขาย", "")
    s3 = sc3.text_input("ชื่อผู้จัดการฝ่ายขาย", "")

    if st.button("🚀 สร้างใบเสนอราคา (Full Option)", type="primary", use_container_width=True):
        doc_info = {"my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
                    "c_name": c_name, "contact": contact, "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax, "c_tax": c_tax,
                    "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "credit": credit, "exp_date": exp_date}
        
        pdf_bytes = create_pdf(doc_info, df_grid, {"subtotal": sub, "vat": vat, "grand_total": grand}, {"s1": s1, "s2": s2, "s3": s3})
        st.download_button("📥 ดาวน์โหลด PDF", data=pdf_bytes, file_name=f"{doc_no}.pdf")

with tab2: st.write("ฐานข้อมูลลูกค้า")
with tab3: st.write("ฐานข้อมูลสินค้า")
