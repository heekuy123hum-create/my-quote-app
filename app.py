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

# --- 2. PDF ENGINE (จัดหน้า A4 ใหม่ให้เป๊ะ) ---
def create_pdf(d, items_df, summary, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    use_f = 'THSarabun' if os.path.exists(font_path) else 'Arial'
    if use_f == 'THSarabun':
        pdf.add_font('THSarabun', '', font_path); pdf.add_font('THSarabun', 'B', font_path)

    # ข้อมูลบริษัทเรา (ขวาบน)
    pdf.set_xy(110, 10); pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(90, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} แฟกซ์: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'R')
    
    pdf.set_y(38); pdf.set_font(use_f, 'B', 22); pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # ข้อมูลลูกค้า และ เอกสาร (ซ้าย-ขวา)
    pdf.set_font(use_f, '', 14); pdf.ln(2); curr_y = pdf.get_y()
    pdf.set_xy(10, curr_y)
    pdf.multi_cell(100, 6, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}\nเลขผู้เสียภาษี: {d['c_tax']}")
    
    pdf.set_xy(110, curr_y)
    pdf.multi_cell(90, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}\nกำหนดส่ง: {d['due_date']}\nเครดิต: {d['credit']} วัน\nราคาเสนอถึง: {d['exp_date']}", 0, 'R')

    # ตารางสินค้า (บีบแถวให้พอหน้าเดียว)
    pdf.set_y(curr_y + 35)
    pdf.set_fill_color(240, 240, 240); pdf.set_font(use_f, 'B', 11)
    w = [15, 65, 18, 15, 25, 22, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    for i in range(len(headers)): pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 11)
    # แสดงเฉพาะแถวที่มีข้อมูล + แถวว่างอีกนิดหน่อยให้พอดีหน้า
    for i in range(12): 
        if i < len(items_df):
            row = items_df.iloc[i]
            val = [str(row.get('รหัสสินค้า','')), str(row.get('รายการ','')), f"{to_num(row.get('qty_num')):,.0f}", 
                   str(row.get('หน่วย','')), f"{to_num(row.get('price_num',0)):,.0f}", f"{to_num(row.get('discount_num',0)):,.0f}", f"{to_num(row.get('รวมเงิน',0)):,.0f}"]
        else: val = [""]*7
        for j in range(7): pdf.cell(w[j], 7, val[j], 1, 0, 'C' if j != 1 else 'L')
        pdf.ln()

    # ยอดรวมเงิน
    pdf.ln(2); pdf.set_font(use_f, 'B', 14)
    pdf.cell(sum(w[:-1]), 7, "รวมเงินย่อย (Sub Total):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{summary['subtotal']:,.0f}", 'B', 1, 'R')
    pdf.cell(sum(w[:-1]), 7, "ภาษี (VAT 7%):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{summary['vat']:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 16); pdf.set_text_color(200, 0, 0)
    pdf.cell(sum(w[:-1]), 9, "ยอดรวมทั้งสิ้น:", 0, 0, 'R'); pdf.cell(w[-1], 9, f"{summary['grand_total']:,.0f}", 'B', 1, 'R')

    # --- ส่วนลายเซ็น (จัดเรียงขวาง 3 ช่อง ชิดล่างสุด) ---
    pdf.set_y(-40) 
    pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 11)
    
    titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    pos_x = [10, 75, 140]

    y_anchor = pdf.get_y()
    for i in range(3):
        pdf.set_xy(pos_x[i], y_anchor)
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_x(pos_x[i])
        pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.set_x(pos_x[i])
        pdf.cell(60, 5, names[i] if names[i] else " ", 0, 1, 'C') # ชื่อเพียวๆ ไม่มีวงเล็บ
        pdf.set_x(pos_x[i])
        pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')

    return bytes(pdf.output())

# --- 3. UI (คืนค่าฟิลด์ข้อมูลให้ครบทุกช่อง) ---
tab1, tab2, tab3 = st.tabs(["📝 ออกใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 ข้อมูลเรา")
        my_comp = st.text_input("ชื่อบริษัทเรา", "SIWAKIT")
        my_addr = st.text_input("ที่อยู่เรา")
        my_tel = st.text_input("โทรเรา")
        my_fax = st.text_input("แฟกซ์เรา")
        my_tax = st.text_input("เลขผู้เสียภาษีเรา")
    with c2:
        st.subheader("📄 ข้อมูลเอกสาร")
        doc_no = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        due_date = st.text_input("กำหนดส่ง", "7 วัน")
        exp_date = st.text_input("ราคาเสนอถึง", "30 วัน")
        credit = st.number_input("เครดิต (วัน)", 0)

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("👤 ข้อมูลลูกค้า")
        c_name = st.text_input("ชื่อบริษัทลูกค้า")
        contact = st.text_input("ชื่อผู้ติดต่อ")
        c_addr = st.text_area("ที่อยู่ลูกค้า", height=68)
    with c4:
        st.write("<br><br>", unsafe_allow_html=True)
        c_tel = st.text_input("เบอร์โทรลูกค้า")
        c_fax = st.text_input("แฟกซ์ลูกค้า")
        c_tax = st.text_input("เลขผู้เสียภาษีลูกค้า")

    st.divider()
    grid = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 12, 
                          num_rows="dynamic", use_container_width=True)
    
    df_grid = pd.DataFrame(grid)
    df_grid['qty_num'] = df_grid['จำนวน'].apply(to_num)
    df_grid['price_num'] = df_grid['ราคา'].apply(to_num)
    df_grid['discount_num'] = df_grid['ส่วนลด'].apply(to_num)
    df_grid['รวมเงิน'] = (df_grid['qty_num'] * df_grid['price_num']) - df_grid['discount_num']
    
    sub = df_grid['รวมเงิน'].sum(); vat = sub * 0.07; grand = sub + vat

    st.subheader("✍️ ลงชื่อผู้เกี่ยวข้อง")
    sc1, sc2, sc3 = st.columns(3)
    s1 = sc1.text_input("ชื่อผู้อนุมัติซื้อ", "")
    s2 = sc2.text_input("ชื่อพนักงานขาย", "")
    s3 = sc3.text_input("ชื่อผู้จัดการฝ่ายขาย", "")

    if st.button("🚀 บันทึกและพิมพ์ PDF (หน้าเดียว)", type="primary", use_container_width=True):
        doc_info = {"my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
                    "c_name": c_name, "contact": contact, "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax, "c_tax": c_tax,
                    "doc_no": doc_no, "doc_date": datetime.now().strftime('%d/%m/%Y'), "due_date": due_date, "credit": credit, "exp_date": exp_date}
        pdf_bytes = create_pdf(doc_info, df_grid, {"subtotal": sub, "vat": vat, "grand_total": grand}, {"s1": s1, "s2": s2, "s3": s3})
        st.download_button("📥 โหลด PDF", data=pdf_bytes, file_name=f"{doc_no}.pdf")

with tab2: st.info("ส่วนจัดการฐานข้อมูลลูกค้า")
with tab3: st.info("ส่วนจัดการฐานข้อมูลสินค้า")
