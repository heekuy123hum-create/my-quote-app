import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os
from fpdf import FPDF

# --- 1. CONFIG & CONNECTION ---
st.set_page_config(page_title="ระบบใบเสนอราคา SIWAKIT (Full Version)", layout="wide")

try:
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=os.environ.get("SUPABASE_URL"), 
                         key=os.environ.get("SUPABASE_KEY"))
except:
    st.warning("⚠️ เชื่อมต่อ Database ไม่ได้ (โปรดตรวจสอบ Secrets)")

def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val else 0.0
    except: return 0.0

# --- 2. PDF ENGINE (จัดหน้าตามแบบ 595.pdf) ---
def create_pdf(d, items_df, summary, sigs):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # การจัดการ Font
    font_path = "THSarabunNew.ttf"
    use_f = 'THSarabun' if os.path.exists(font_path) else 'Arial'
    if use_f == 'THSarabun':
        pdf.add_font('THSarabun', '', font_path); pdf.add_font('THSarabun', 'B', font_path)

    # 1. โลโก้ (มุมซ้ายบน)
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
    
    # 2. ข้อมูลบริษัทเรา (ถัดจากโลโก้)
    pdf.set_xy(35, 10); pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(100, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # 3. ช่องสี่เหลี่ยมขวาบน (เลขที่ และ วันที่)
    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 14, "", 1, 0) # ตีกรอบ
    pdf.set_xy(146, 11)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    # 4. หัวข้อหลัก
    pdf.set_y(42); pdf.set_font(use_f, 'B', 22); pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # 5. ข้อมูลลูกค้า และ ข้อมูลเงื่อนไข (อยู่ระนาบเดียวกัน)
    pdf.set_font(use_f, '', 14); pdf.ln(2); curr_y = pdf.get_y()
    
    # ฝั่งซ้าย: ลูกค้า (ไม่มีเลขผู้เสียภาษีตามสั่ง)
    pdf.set_xy(10, curr_y)
    pdf.multi_cell(115, 6, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}")
    
    # ฝั่งขวา: เงื่อนไขการส่ง (ระดับเดียวกับลูกค้า)
    pdf.set_xy(125, curr_y)
    pdf.multi_cell(75, 6, f"กำหนดส่ง: {d['due_date']}\nเครดิต: {d['credit']} วัน\nราคาเสนอถึง: {d['exp_date']}", 0, 'L')

    # 6. ตารางสินค้า (บังคับ 20 แถว)
    pdf.set_y(curr_y + 35)
    pdf.set_fill_color(240, 240, 240); pdf.set_font(use_f, 'B', 10)
    w = [15, 70, 15, 15, 25, 20, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จํานวนเงิน"]
    for i in range(len(headers)): pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 10)
    for i in range(20):
        if i < len(items_df):
            row = items_df.iloc[i]
            val = [str(row.get('รหัสสินค้า','')), str(row.get('รายการ','')), f"{to_num(row.get('จำนวน')):,.0f}", 
                   str(row.get('หน่วย','')), f"{to_num(row.get('ราคา')):,.0f}", f"{to_num(row.get('ส่วนลด')):,.0f}", f"{to_num(row.get('รวมเงิน',0)):,.0f}"]
        else: val = [""]*7
        # กรองแถวว่างถ้าไม่มีชื่อรายการ
        if i >= len(items_df) or (str(items_df.iloc[i].get('รายการ','')).strip() == ""):
            val = [""]*7
            
        for j in range(7): pdf.cell(w[j], 6, val[j], 1, 0, 'C' if j != 1 else 'L')
        pdf.ln()

    # 7. ยอดเงินสรุป
    pdf.ln(1); pdf.set_font(use_f, 'B', 12)
    pdf.cell(sum(w[:-1]), 6, "รวมเงินย่อย (Sub Total):", 0, 0, 'R'); pdf.cell(w[-1], 6, f"{summary['subtotal']:,.0f}", 'B', 1, 'R')
    pdf.cell(sum(w[:-1]), 6, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R'); pdf.cell(w[-1], 6, f"{summary['vat']:,.0f}", 'B', 1, 'R')
    pdf.set_font(use_f, 'B', 14); pdf.set_text_color(200, 0, 0)
    pdf.cell(sum(w[:-1]), 8, "ยอดรวมทั้งสิ้น (Grand Total):", 0, 0, 'R'); pdf.cell(w[-1], 8, f"{summary['grand_total']:,.0f}", 'B', 1, 'R')

    # 8. ลายเซ็น (เรียงหน้ากระดาน 3 ช่อง ชิดล่างสุด หน้าเดียวจบ)
    pdf.set_y(-35) 
    pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 11)
    titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    pos_x = [10, 75, 140]
    y_anchor = pdf.get_y()
    
    for i in range(3):
        pdf.set_xy(pos_x[i], y_anchor)
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_x(pos_x[i]); pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.set_x(pos_x[i]); pdf.cell(60, 5, names[i] if names[i] else " ", 0, 1, 'C')
        pdf.set_x(pos_x[i]); pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')

    return bytes(pdf.output())

# --- 3. UI (หน้าจอหลัก) ---
st.title("🚀 SIWAKIT Quotation System")

tab1, tab2, tab3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัทเรา", "SIWAKIT")
        my_addr = st.text_input("ที่อยู่บริษัทเรา")
        my_tel = st.text_input("เบอร์โทรศัพท์")
        my_fax = st.text_input("เบอร์โทรสาร")
        my_tax = st.text_input("เลขประจำตัวผู้เสียภาษี")
    with col2:
        st.subheader("📄 ข้อมูลเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        doc_date = st.text_input("วันที่เอกสาร", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("กำหนดส่งสินค้า", "7 วัน")
        exp_date = st.text_input("ยืนราคาถึงวันที่", "30 วัน")
        credit = st.number_input("เครดิต (จำนวนวัน)", 0)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("👤 ข้อมูลลูกค้า")
        c_name = st.text_input("ชื่อบริษัทลูกค้า")
        contact = st.text_input("ชื่อผู้ติดต่อ")
        c_addr = st.text_area("ที่อยู่ลูกค้า", height=65)
    with col4:
        st.write("<br>", unsafe_allow_html=True)
        c_tel = st.text_input("โทรศัพท์ลูกค้า")
        c_fax = st.text_input("โทรสารลูกค้า")

    st.subheader("🛒 รายการสินค้า")
    # ตารางแบบกรอกข้อมูลได้ 20 แถว
    grid_data = st.data_editor([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 20, 
                               num_rows="dynamic", use_container_width=True)
    
    df_grid = pd.DataFrame(grid_data)
    df_grid['qty_num'] = df_grid['จำนวน'].apply(to_num)
    df_grid['price_num'] = df_grid['ราคา'].apply(to_num)
    df_grid['discount_num'] = df_grid['ส่วนลด'].apply(to_num)
    df_grid['รวมเงิน'] = (df_grid['qty_num'] * df_grid['price_num']) - df_grid['discount_num']
    
    subtotal = df_grid['รวมเงิน'].sum()
    vat = subtotal * 0.07
    grand_total = subtotal + vat

    st.divider()
    st.subheader("✍️ ลงชื่อผู้เกี่ยวข้อง")
    s_col1, s_col2, s_col3 = st.columns(3)
    sig_1 = s_col1.text_input("ชื่อผู้อนุมัติซื้อ (ลูกค้า)")
    sig_2 = s_col2.text_input("ชื่อพนักงานขาย")
    sig_3 = s_col3.text_input("ชื่อผู้จัดการฝ่ายขาย")

    if st.button("🖨️ ออกใบเสนอราคา (PDF)", type="primary", use_container_width=True):
        doc_data = {
            "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
            "c_name": c_name, "contact": contact, "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax,
            "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "credit": credit, "exp_date": exp_date
        }
        
        pdf_out = create_pdf(doc_data, df_grid, {"subtotal": subtotal, "vat": vat, "grand_total": grand_total}, 
                            {"s1": sig_1, "s2": sig_2, "s3": sig_3})
        
        st.success("✅ สร้างไฟล์สำเร็จ!")
        st.download_button("📥 ดาวน์โหลดใบเสนอราคา", data=pdf_out, file_name=f"{doc_no}.pdf", mime="application/pdf")

with tab2:
    st.info("💡 เชื่อมต่อกับฐานข้อมูล Supabase เพื่อดึงรายชื่อลูกค้าที่บันทึกไว้")
    # ส่วนนี้สามารถเพิ่มโค้ดดึงข้อมูลจาก supabase ได้ตามต้องการ

with tab3:
    st.info("💡 จัดการรหัสสินค้าและราคามาตรฐาน")
