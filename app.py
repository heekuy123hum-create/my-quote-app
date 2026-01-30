import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

# ==========================================
# 1. INITIAL CONFIGURATION
# ==========================================
st.set_page_config(page_title="SIWAKIT Quotation System (Full)", layout="wide")

# ระบบเชื่อมต่อ Database (คงไว้สำหรับการขยายระบบใน Tab 2 และ 3)
try:
    from st_supabase_connection import SupabaseConnection
    if os.environ.get("SUPABASE_URL"):
        conn = st.connection("supabase", type=SupabaseConnection)
    else:
        conn = None
except Exception:
    conn = None

def to_num(val):
    """ฟังก์ชันจัดการตัวเลข ป้องกัน Error เวลาคำนวณเงิน"""
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val else 0.0
    except: return 0.0

# ==========================================
# 2. PDF GENERATION ENGINE
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text):
    # ตั้งค่ากระดาษ A4
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # โหลดฟอนต์ภาษาไทย
    font_path = "THSarabunNew.ttf"
    use_f = 'THSarabun' if os.path.exists(font_path) else 'Arial'
    if use_f == 'THSarabun':
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)

    # --- HEADER SECTION ---
    # โลโก้บริษัท
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
            
    # ข้อมูลบริษัทเรา
    pdf.set_xy(35, 10)
    pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(100, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # กรอบเลขที่เอกสาร
    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0)
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    # ชื่อหัวเอกสาร
    pdf.set_y(42)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # --- CUSTOMER & CONDITIONS SECTION ---
    pdf.set_font(use_f, '', 14)
    pdf.ln(2)
    start_y = pdf.get_y()
    
    # [ฝั่งซ้าย] ข้อมูลลูกค้า
    pdf.set_xy(10, start_y)
    pdf.multi_cell(115, 6, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}")
    y_left = pdf.get_y()
    
    # [ฝั่งขวา] เงื่อนไขการขาย
    pdf.set_xy(130, start_y)
    pdf.multi_cell(75, 6, f"วันที่กำหนดส่ง: {d['due_date']}\nยืนราคา (วัน): {d['valid_days']}  Expire Date: {d['exp_date']}\nเครดิต (วัน): {d['credit']}", 0, 'L')
    y_right = pdf.get_y()
    
    # คำนวณจุดเริ่มตาราง
    table_start_y = max(y_left, y_right) + 5
    pdf.set_y(table_start_y)

    # --- TABLE SECTION ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 11)
    w = [15, 75, 15, 15, 25, 15, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    for i in range(len(headers)):
        pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    # ตารางสินค้า (ปรับ Row Height ให้เล็กลงเหลือ 6.0 เพื่อดึงพื้นที่คืนมา)
    pdf.set_font(use_f, '', 11)
    row_height = 6.0  # ลดจาก 6.5 -> 6.0 (20 บรรทัดจะประหยัดที่ได้ 10mm)
    for i in range(20):
        if i < len(items_df):
            row = items_df.iloc[i]
            if str(row.get('รายการ','')).strip() != "":
                val = [
                    str(row.get('รหัสสินค้า','')), 
                    str(row.get('รายการ','')), 
                    f"{to_num(row.get('จำนวน')):,.0f}", 
                    str(row.get('หน่วย','')), 
                    f"{to_num(row.get('ราคา')):,.0f}", 
                    f"{to_num(row.get('ส่วนลด')):,.0f}", 
                    f"{to_num(row.get('รวมเงิน',0)):,.0f}"
                ]
            else: val = [""]*7
        else: val = [""]*7
        
        for j in range(7):
            align = 'L' if j == 1 else 'C'
            if j == 6: align = 'R'
            pdf.cell(w[j], row_height, val[j], 1, 0, align)
        pdf.ln()

    # --- FOOTER & FINANCIAL SUMMARY SECTION ---
    # *จุดแก้ไขสำคัญ*: ขยับจุดเริ่มสรุปขึ้นไปเกือบติดตาราง (เว้นแค่ 2mm)
    current_y_after_table = pdf.get_y()
    pdf.set_y(current_y_after_table + 2) 
    
    sum_y = pdf.get_y()
    
    # 1. หมายเหตุ (ฝั่งซ้าย)
    pdf.set_xy(10, sum_y)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12)
    pdf.set_x(10)
    pdf.multi_cell(105, 5, remark_text, 0, 'L')
    
    # 2. ยอดเงิน (ฝั่งขวา)
    labels_x = 125 
    values_x = 175 
    sum_line_h = 5.0 # ลดความสูงบรรทัดสรุปให้กระชับ

    def add_sum_row(label, value, is_bold=False, is_red=False):
        pdf.set_font(use_f, 'B' if is_bold else '', 13 if is_bold else 12)
        if is_red: pdf.set_text_color(180, 0, 0)
        else: pdf.set_text_color(0, 0, 0)
        
        # ใช้เทคนิคจำตำแหน่ง Y เพื่อให้บรรทัดต่อกันสนิท
        curr_y = pdf.get_y()
        pdf.set_xy(labels_x, curr_y)
        pdf.cell(45, sum_line_h, label, 0, 0, 'R')
        pdf.set_xy(values_x, curr_y)
        pdf.cell(25, sum_line_h, f"{value:,.2f}", 'B', 1, 'R')

    # เขียนแต่ละบรรทัด
    add_sum_row("รวมเงินย่อย (Gross Total):", summary['gross'])
    add_sum_row("ส่วนลด (Total Discount):", summary['discount'])
    add_sum_row("หลังหักส่วนลด (Sub Total):", summary['subtotal'])
    add_sum_row("ภาษีมูลค่าเพิ่ม (VAT 7%):", summary['vat'])
    add_sum_row("ยอดรวมทั้งสิ้น (Grand Total):", summary['grand_total'], True, True)

    # 3. ลายเซ็น (ล็อกตำแหน่งล่างสุดเหมือนเดิม)
    # ตอนนี้สรุปยอดจะอยู่สูงขึ้นมาก ทำให้ไม่ทับลายเซ็นแน่นอน
    pdf.set_y(-35)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(use_f, '', 11)
    titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    pos_x = [10, 75, 140]
    
    y_sig = pdf.get_y()
    for i in range(3):
        pdf.set_xy(pos_x[i], y_sig)
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_sig + 5); pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_sig + 10); pdf.cell(60, 5, f"({names[i]})" if names[i] else "(...................................................)", 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_sig + 15); pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')

    return bytes(pdf.output())

# ==========================================
# 3. USER INTERFACE SECTION
# ==========================================
st.title("🚀 SIWAKIT Enterprise Quotation System")

tab1, tab2, tab3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 คลังสินค้า"])

with tab1:
    # --- ข้อมูล Header ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัท", "SIWAKIT")
        my_addr = st.text_input("ที่อยู่บริษัท")
        my_tel = st.text_input("โทรศัพท์", "02-xxx-xxxx")
        my_fax = st.text_input("โทรสาร (Fax)", "-")
        my_tax = st.text_input("เลขผู้เสียภาษี", "1234567890123")
    with c2:
        st.subheader("📄 รายละเอียดเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        doc_date = st.text_input("วันที่ออกเอกสาร", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("วันที่กำหนดส่ง", "7 วัน")
        
        col_v1, col_v2 = st.columns(2)
        valid_days = col_v1.text_input("ยืนราคา (วัน)", "30")
        exp_date = col_v2.text_input("Expire Date", datetime.now().strftime('%d/%m/%Y'))
        credit = st.text_input("เครดิตการชำระเงิน (วัน)", "30")

    st.divider()

    # --- ข้อมูลลูกค้า ---
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("👤 ข้อมูลลูกค้า")
        c_name = st.text_input("ชื่อบริษัทลูกค้า")
        contact = st.text_input("ชื่อผู้ติดต่อ")
        c_addr = st.text_area("ที่อยู่จัดส่ง/วางบิล", height=70)
    with c4:
        st.write("<br><br>", unsafe_allow_html=True)
        c_tel = st.text_input("เบอร์โทรศัพท์ลูกค้า")
        c_fax = st.text_input("เบอร์แฟกซ์ลูกค้า")

    # --- ตารางแก้ไขข้อมูล ---
    st.subheader("📦 รายการสินค้า")
    grid = st.data_editor(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 20, 
        num_rows="dynamic", use_container_width=True
    )
    
    # --- การคำนวณยอดเงิน ---
    df = pd.DataFrame(grid)
    df['qty_n'] = df['จำนวน'].apply(to_num)
    df['pri_n'] = df['ราคา'].apply(to_num)
    df['dis_n'] = df['ส่วนลด'].apply(to_num)
    df['รวมเงิน'] = (df['qty_n'] * df['pri_n']) - df['dis_n']
    
    gross_total = (df['qty_n'] * df['pri_n']).sum()
    total_discount = df['dis_n'].sum()
    subtotal = df['รวมเงิน'].sum()
    vat = subtotal * 0.07
    grand_total = subtotal + vat

    # --- ส่วนท้ายหน้าจอ ---
    cf1, cf2 = st.columns([2, 1])
    with cf1:
        remark = st.text_area("📝 หมายเหตุ (Remark)", value="1. สินค้ารับประกัน 1 ปี\n2. กำหนดยืนราคาตามที่ระบุในเอกสาร")
    with cf2:
        st.write("### สรุปยอดเงิน")
        st.write(f"รวมเป็นเงิน: {gross_total:,.2f}")
        st.write(f"ส่วนลดทั้งหมด: -{total_discount:,.2f}")
        st.write(f"ยอดหลังหักส่วนลด: {subtotal:,.2f}")
        st.write(f"ภาษีมูลค่าเพิ่ม 7%: {vat:,.2f}")
        st.metric("ยอดรวมทั้งสิ้น", f"{grand_total:,.2f} บาท")

    # --- ลายเซ็น ---
    sc1, sc2, sc3 = st.columns(3)
    sig1 = sc1.text_input("ชื่อผู้อนุมัติซื้อ (ลูกค้า)")
    sig2 = sc2.text_input("ชื่อพนักงานขาย")
    sig3 = sc3.text_input("ชื่อผู้จัดการฝ่ายขาย")

    # --- ปุ่ม Generate ---
    if st.button("🚀 สร้างเอกสาร PDF (เวอร์ชันสมบูรณ์)", type="primary", use_container_width=True):
        doc_data = {
            "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
            "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "valid_days": valid_days, 
            "exp_date": exp_date, "credit": credit, "c_name": c_name, "contact": contact, 
            "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax
        }
        
        pdf_res = create_pdf(
            doc_data, df, 
            {"gross": gross_total, "discount": total_discount, "subtotal": subtotal, "vat": vat, "grand_total": grand_total}, 
            {"s1": sig1, "s2": sig2, "s3": sig3}, 
            remark
        )
        
        st.success("✅ สร้างไฟล์ PDF เรียบร้อยแล้ว!")
        st.download_button("📥 ดาวน์โหลดใบเสนอราคา", pdf_res, f"{doc_no}.pdf", "application/pdf")

with tab2: st.info("ระบบจัดการฐานข้อมูลลูกค้า (ยังไม่เปิดใช้งาน)")
with tab3: st.info("ระบบจัดการคลังสินค้า (ยังไม่เปิดใช้งาน)")
