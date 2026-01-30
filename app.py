import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
st.set_page_config(page_title="ระบบใบเสนอราคา SIWAKIT (Ultimate)", layout="wide")

# เชื่อมต่อ Database (ถ้ามี)
try:
    from st_supabase_connection import SupabaseConnection
    if os.environ.get("SUPABASE_URL"):
        conn = st.connection("supabase", type=SupabaseConnection)
    else:
        conn = None
except Exception:
    conn = None

def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val else 0.0
    except: return 0.0

# ==========================================
# 2. PDF GENERATION ENGINE
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text):
    # ตั้งค่าหน้า A4
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # ฟอนต์
    font_path = "THSarabunNew.ttf"
    use_f = 'THSarabun' if os.path.exists(font_path) else 'Arial'
    if use_f == 'THSarabun':
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)

    # --- HEADER ---
    # 1. โลโก้
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
            
    # 2. ข้อมูลบริษัทเรา
    pdf.set_xy(35, 10)
    pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(100, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # 3. กรอบเลขที่ (ขวาบน)
    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0)
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    # 4. หัวข้อ
    pdf.set_y(42)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # --- CUSTOMER & INFO (แก้เรื่องทับกันตรงนี้) ---
    pdf.set_font(use_f, '', 14)
    pdf.ln(2)
    
    start_y = pdf.get_y()
    
    # ฝั่งซ้าย: ลูกค้า
    pdf.set_xy(10, start_y)
    pdf.multi_cell(115, 6, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}")
    y_left = pdf.get_y()
    
    # ฝั่งขวา: เงื่อนไข
    pdf.set_xy(130, start_y)
    pdf.multi_cell(70, 6, f"วันที่กำหนดส่ง: {d['due_date']}\nยืนราคา(วัน): Expire Date: {d['exp_date']}\nเครดิต (วัน): {d['credit']}", 0, 'L')
    y_right = pdf.get_y()
    
    # *** คำนวณจุดเริ่มตารางอัตโนมัติ ***
    # เลือกจุดที่ต่ำที่สุดระหว่างซ้ายกับขวา แล้วบวกเพิ่ม 5mm ไม่ให้ชิดเกินไป
    table_start_y = max(y_left, y_right) + 5
    pdf.set_y(table_start_y)

    # --- TABLE ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 11)
    w = [15, 75, 15, 15, 25, 15, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    for i in range(len(headers)):
        pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 11)
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
            pdf.cell(w[j], 7, val[j], 1, 0, align)
        pdf.ln()

    # --- SUMMARY & REMARK (เพิ่มส่วนนี้) ---
    pdf.ln(2)
    current_y_sum = pdf.get_y()
    
    # 1. หมายเหตุ (ฝั่งซ้าย)
    pdf.set_xy(10, current_y_sum)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12)
    pdf.multi_cell(100, 6, remark_text, 0, 'L')
    
    # 2. คำนวณเงิน (ฝั่งขวา) - เพิ่มบรรทัดส่วนลดให้ครบ
    pdf.set_xy(120, current_y_sum)
    
    # รวมเงิน (Gross)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(60, 6, "รวมเงิน (Gross Total):", 0, 0, 'R')
    pdf.cell(30, 6, f"{summary['gross']:,.0f}", 'B', 1, 'R'); pdf.ln()
    
    # หักส่วนลด (Discount)
    pdf.set_x(120)
    pdf.cell(60, 6, "หักส่วนลด (Discount):", 0, 0, 'R')
    pdf.cell(30, 6, f"{summary['discount']:,.0f}", 'B', 1, 'R'); pdf.ln()
    
    # หลังหักส่วนลด (Subtotal)
    pdf.set_x(120)
    pdf.cell(60, 6, "หลังหักส่วนลด (Sub Total):", 0, 0, 'R')
    pdf.cell(30, 6, f"{summary['subtotal']:,.0f}", 'B', 1, 'R'); pdf.ln()
    
    # VAT
    pdf.set_x(120)
    pdf.cell(60, 6, "ภาษีมูลค่าเพิ่ม (VAT 7%):", 0, 0, 'R')
    pdf.cell(30, 6, f"{summary['vat']:,.0f}", 'B', 1, 'R'); pdf.ln()
    
    # Grand Total
    pdf.set_x(120)
    pdf.set_font(use_f, 'B', 14); pdf.set_text_color(180, 0, 0)
    pdf.cell(60, 8, "ยอดรวมทั้งสิ้น (Grand Total):", 0, 0, 'R')
    pdf.cell(30, 8, f"{summary['grand_total']:,.0f}", 'B', 1, 'R')

    # --- SIGNATURES ---
    # ล็อกตำแหน่งล่างสุด (-35mm)
    pdf.set_y(-35) 
    pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 11)
    
    titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    pos_x = [10, 75, 140]
    
    y_anchor = pdf.get_y()
    for i in range(3):
        pdf.set_xy(pos_x[i], y_anchor)
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_anchor + 5); pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_anchor + 10); pdf.cell(60, 5, f"({names[i]})" if names[i] else "(...................................................)", 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_anchor + 15); pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')

    return bytes(pdf.output())

# ==========================================
# 3. UI (หน้าจอ)
# ==========================================
st.title("🚀 ระบบใบเสนอราคา SIWAKIT (Full Version)")

tab1, tab2, tab3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า"])

with tab1:
    # Header
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัท", "SIWAKIT")
        my_addr = st.text_input("ที่อยู่", "123/45 ถนนตัวอย่าง ...")
        my_tel = st.text_input("โทรศัพท์", "02-xxx-xxxx")
        my_fax = st.text_input("โทรสาร", "-")
        my_tax = st.text_input("เลขผู้เสียภาษี", "1234567890123")
    with c2:
        st.subheader("📄 รายละเอียดเอกสาร")
        doc_no = st.text_input("เลขที่", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        doc_date = st.text_input("วันที่", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("กำหนดส่ง", "7 วัน")
        exp_date = st.text_input("ยืนราคา(วัน) Expire Date", "30 วัน")
        credit = st.text_input("เครดิต (วัน)", "30")

    st.divider()

    # Customer
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("👤 ข้อมูลลูกค้า")
        c_name = st.text_input("ชื่อบริษัทลูกค้า")
        contact = st.text_input("ชื่อผู้ติดต่อ")
        c_addr = st.text_area("ที่อยู่ลูกค้า", height=80)
    with c4:
        st.write("<br><br>", unsafe_allow_html=True)
        c_tel = st.text_input("เบอร์โทรลูกค้า")
        c_fax = st.text_input("เบอร์แฟกซ์ลูกค้า")

    st.divider()

    # Table
    st.subheader("📦 รายการสินค้า (20 บรรทัด)")
    default_data = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0} for _ in range(20)]
    grid = st.data_editor(default_data, num_rows="dynamic", use_container_width=True, height=600)
    
    # Calculations
    df_grid = pd.DataFrame(grid)
    df_grid['qty_num'] = df_grid['จำนวน'].apply(to_num)
    df_grid['price_num'] = df_grid['ราคา'].apply(to_num)
    df_grid['discount_num'] = df_grid['ส่วนลด'].apply(to_num)
    
    # คำนวณยอดเงินแต่ละแถว (ราคา * จำนวน - ส่วนลด)
    df_grid['รวมเงิน'] = (df_grid['qty_num'] * df_grid['price_num']) - df_grid['discount_num']
    
    # คำนวณยอดสรุป
    gross_total = (df_grid['qty_num'] * df_grid['price_num']).sum() # ยอดรวมก่อนหักส่วนลด
    total_discount = df_grid['discount_num'].sum() # รวมส่วนลดทั้งหมด
    subtotal = df_grid['รวมเงิน'].sum() # ยอดหลังหักส่วนลด
    vat = subtotal * 0.07
    grand_total = subtotal + vat
    
    # แสดงยอด Realtime
    c_res1, c_res2 = st.columns([2, 1])
    with c_res1:
        st.text_area("📝 หมายเหตุ (Remark)", key="remark_input", height=100)
    with c_res2:
        st.metric("ยอดรวมทั้งสิ้น", f"{grand_total:,.2f} บาท")
        st.write(f"รวมเป็นเงิน: {gross_total:,.2f}")
        st.write(f"ส่วนลด: -{total_discount:,.2f}")
        st.write(f"หลังหักส่วนลด: {subtotal:,.2f}")
        st.write(f"VAT 7%: {vat:,.2f}")

    # Signatures
    st.subheader("✍️ ผู้ลงนาม")
    sc1, sc2, sc3 = st.columns(3)
    s1 = sc1.text_input("ผู้อนุมัติซื้อ"); s2 = sc2.text_input("พนักงานขาย"); s3 = sc3.text_input("ผู้จัดการฝ่ายขาย")

    # Generate PDF Button
    st.markdown("---")
    if st.button("🚀 สร้างและดาวน์โหลด PDF (สมบูรณ์ 100%)", type="primary", use_container_width=True):
        doc_info = {
            "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
            "c_name": c_name, "contact": contact, "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax,
            "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "credit": credit, "exp_date": exp_date
        }
        
        pdf_bytes = create_pdf(
            doc_info, df_grid, 
            {
                "gross": gross_total, 
                "discount": total_discount, 
                "subtotal": subtotal, 
                "vat": vat, 
                "grand_total": grand_total
            }, 
            {"s1": s1, "s2": s2, "s3": s3},
            st.session_state.remark_input # ส่งค่าหมายเหตุไปพิมพ์
        )
        
        st.success("✅ สร้างไฟล์สำเร็จ!")
        st.download_button("📥 ดาวน์โหลด PDF", data=pdf_bytes, file_name=f"{doc_no}.pdf", mime="application/pdf")

with tab2: st.info("ฐานข้อมูลลูกค้า (System Ready)")
with tab3: st.info("ฐานข้อมูลสินค้า (System Ready)")
