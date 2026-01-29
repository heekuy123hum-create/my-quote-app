import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & CONNECTION ---
st.set_page_config(page_title="ระบบใบเสนอราคา Full Version", layout="wide")

try:
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=os.environ.get("SUPABASE_URL"), 
                         key=os.environ.get("SUPABASE_KEY"))
except:
    st.error("เชื่อมต่อ Database ไม่ได้")
    st.stop()

def fetch_customers():
    res = conn.table("customers").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['id', 'name', 'address', 'tel', 'fax', 'tax_id', 'contact'])

# --- 2. PDF ENGINE (ห้ามตัดฟิลด์ไหนออกเด็ดขาด) ---
def create_pdf(d, items_df, summary, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path); pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else: use_f = 'Arial'

    # ส่วนหัว: ข้อมูลบริษัทเรา (ฝั่งขวาตาม แห.pdf)
    logo = next((f"logo.{ext}" for ext in ['png','jpg','jpeg'] if os.path.exists(f"logo.{ext}")), None)
    if logo: pdf.image(logo, x=10, y=10, w=25)

    pdf.set_xy(110, 10); pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(90, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'R')

    pdf.set_y(38); pdf.set_font(use_f, 'B', 24); pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # ข้อมูลลูกค้า และ ข้อมูลเอกสาร
    pdf.set_font(use_f, '', 14); pdf.ln(2); curr_y = pdf.get_y()
    pdf.set_xy(10, curr_y)
    pdf.multi_cell(100, 7, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}\nเลขผู้เสียภาษี: {d['c_tax']}")
    
    pdf.set_xy(110, curr_y)
    pdf.multi_cell(90, 7, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}\nวันที่กำหนดส่ง: {d['due_date']}\nเครดิต: {d['credit']} วัน\nราคาเสนอถึงวันที่: {d['exp_date']}", 0, 'R')

    # ตารางสินค้า (7 คอลัมน์ตาม แห.pdf)
    pdf.set_y(curr_y + 42)
    pdf.set_fill_color(240, 240, 240); pdf.set_font(use_f, 'B', 11)
    w = [15, 65, 18, 15, 25, 22, 30] # รหัส, รายการ, จำนวน, หน่วย, ราคา, ส่วนลด, รวมเงิน
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    for i in range(len(headers)): pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 11)
    for i in range(18):
        if i < len(items_df):
            row = items_df.iloc[i]
            val = [str(row['รหัสสินค้า']), str(row['รายการ']), f"{row['qty_num']:,.0f}", str(row['หน่วย']), 
                   f"{row['price_num']:,.0f}", f"{row['discount_num']:,.0f}", f"{row['รวมเงิน']:,.0f}"]
        else: val = [""]*7
        for j in range(7): pdf.cell(w[j], 7, val[j], 1, 0, 'C' if j != 1 else 'L')
        pdf.ln()

    # สรุปยอดเงิน
    pdf.ln(2); pdf.set_font(use_f, 'B', 14)
    pdf.cell(sum(w[:-1]), 7, "รวมเงินย่อย (Sub Total):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{summary['subtotal']:,.0f}", 'B', 1, 'R')
    pdf.cell(sum(w[:-1]), 7, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R'); pdf.cell(w[-1], 7, f"{summary['vat']:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 16); pdf.set_text_color(200, 0, 0)
    pdf.cell(sum(w[:-1]), 9, "ยอดรวมทั้งสิ้น:", 0, 0, 'R'); pdf.cell(w[-1], 9, f"{summary['grand_total']:,.0f}", 'B', 1, 'R')

    # ลายเซ็น (ชิดขอบล่าง พร้อมตำแหน่งและชื่อกรอก)
    pdf.set_y(-48); pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 12)
    titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    for i in range(3):
        pdf.set_xy(10 + (i*65), pdf.get_y())
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.cell(60, 5, f"( {names[i]} )", 0, 1, 'C')
        pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')
        pdf.set_y(pdf.get_y() - 20)

    return bytes(pdf.output())

# --- 3. UI (เวอร์ชันเต็ม ทุกช่องกรอกได้) ---
tab1, tab2, tab3 = st.tabs(["📝 ออกใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า"])

with tab1:
    df_c = fetch_customers()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 ข้อมูลบริษัทเรา")
        my_comp = st.text_input("ชื่อบริษัทเรา", "SIWAKIT")
        my_addr = st.text_area("ที่อยู่บริษัทเรา", "123/45 ถนน... จังหวัด...", height=65)
        my_tel = st.text_input("เบอร์โทรเรา")
        my_fax = st.text_input("โทรสารเรา")
        my_tax = st.text_input("เลขผู้เสียภาษีเรา")
    with col2:
        st.subheader("📄 ข้อมูลเอกสาร")
        doc_no = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        doc_date = st.text_input("วันที่", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("กำหนดส่ง", "7 วัน")
        exp_date = st.text_input("ราคาเสนอถึง", "30 วัน")
        credit = st.number_input("เครดิต (วัน)", 0)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("👤 ข้อมูลลูกค้า")
        sid = st.selectbox("ดึงจากฐานข้อมูล", ["-- พิมพ์เอง --"] + df_c['id'].astype(str).tolist())
        target = df_c[df_c['id'].astype(str) == sid].iloc[0] if sid != "-- พิมพ์เอง --" else {}
        c_name = st.text_input("บริษัทลูกค้า", value=target.get('name', ''))
        contact = st.text_input("ชื่อผู้ติดต่อ", value=target.get('contact', ''))
        c_addr = st.text_area("ที่อยู่ลูกค้า", value=target.get('address', ''), height=100)
    with col4:
        st.write("<br><br>", unsafe_allow_html=True)
        c_tel = st.text_input("โทรลูกค้า", value=target.get('tel', ''))
        c_fax = st.text_input("โทรสารลูกค้า", value=target.get('fax', ''))
        c_tax = st.text_input("เลขผู้เสียภาษีลูกค้า", value=target.get('tax_id', ''))

    st.divider()
    grid = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 20, 
                          num_rows="dynamic", use_container_width=True)
    
    df_grid = pd.DataFrame(grid)
    for col in ['จำนวน', 'ราคา', 'ส่วนลด']: df_grid[f'{col}_num'] = pd.to_numeric(df_grid[col], errors='coerce').fillna(0)
    df_grid['รวมเงิน'] = (df_grid['qty_num'] * df_grid['price_num']) - df_grid['ส่วนลด_num']
    
    sub = int(df_grid['รวมเงิน'].sum()); vat = int(sub * 0.07); grand = sub + vat

    st.subheader("✍️ ผู้ลงนาม")
    sc1, sc2, sc3 = st.columns(3)
    s1 = sc1.text_input("ชื่อผู้อนุมัติซื้อ", "")
    s2 = sc2.text_input("ชื่อพนักงานขาย", "")
    s3 = sc3.text_input("ชื่อผู้จัดการฝ่ายขาย", "")

    if st.button("🔥 บันทึกและสร้างใบเสนอราคา", type="primary", use_container_width=True):
        if c_name:
            cust_data = {"name": c_name, "contact": contact, "address": c_addr, "tel": c_tel, "fax": c_fax, "tax_id": c_tax}
            if sid != "-- พิมพ์เอง --": conn.table("customers").update(cust_data).eq("id", sid).execute()
            
            doc_info = {"my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
                        "c_name": c_name, "contact": contact, "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax, "c_tax": c_tax,
                        "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "credit": credit, "exp_date": exp_date}
            
            pdf_bytes = create_pdf(doc_info, df_grid, {"subtotal": sub, "vat": vat, "grand_total": grand}, {"s1": s1, "s2": s2, "s3": s3})
            st.success("บันทึกและสร้าง PDF สำเร็จ!")
            st.download_button("📥 โหลดไฟล์ PDF", data=pdf_bytes, file_name=f"{doc_no}.pdf")

with tab2:
    st.subheader("รายชื่อลูกค้าในฐานข้อมูล")
    st.dataframe(fetch_customers())
with tab3:
    st.info("ระบบจัดการสินค้า")
