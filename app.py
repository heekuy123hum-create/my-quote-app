import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import json
from fpdf import FPDF

# ==========================================
# 1. การตั้งค่าระบบ (SYSTEM CONFIGURATION)
# ==========================================
st.set_page_config(page_title="SIWAKIT TRADING SYSTEM", layout="wide", page_icon="🏢")

# --- CSS ตกแต่ง (คงเดิมแต่จัดเต็ม) ---
st.markdown("""
<style>
    /* ปรับฟอนต์หลัก */
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
    }
    /* หัวข้อ */
    h1, h2, h3 {
        color: #2c3e50;
    }
    /* ปรับแต่งปุ่มกด */
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
        border: 1px solid #ddd;
    }
    .stButton>button:hover {
        border-color: #4CAF50;
        color: #4CAF50;
    }
    /* กล่องยอดเงินรวม */
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #28a745;
        padding: 20px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: right;
    }
    .metric-label {
        font-size: 1.1rem;
        color: #6c757d;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #28a745;
    }
    .metric-sub {
        font-size: 0.9rem;
        color: #555;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ชื่อไฟล์สำหรับเก็บข้อมูล
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"
HISTORY_FILE = "history_quotes.csv"
FONT_PATH = "THSarabunNew.ttf" # ⚠️ ต้องมีไฟล์นี้

# ==========================================
# 2. จัดการ SESSION STATE (ตัวแปรระบบ)
# ==========================================
# เริ่มต้นตัวแปรตารางสินค้า
if "grid_df" not in st.session_state:
    # สร้างแถวเปล่า 15 บรรทัดเตรียมไว้
    st.session_state.grid_df = pd.DataFrame(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0.0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 15
    )

# เริ่มต้นตัวแปรสำหรับ Input Fields เพื่อให้ Restore ค่าได้
default_keys = [
    "c_name_in", "contact_in", "c_addr_in", "c_tel_in", "c_fax_in", 
    "doc_no_in", "remark_in", "s1_in", "s2_in", "s3_in",
    "my_comp_in", "my_addr_in", "my_tel_in", "my_fax_in", "my_tax_in"
]
for key in default_keys:
    if key not in st.session_state:
        st.session_state[key] = ""

# ==========================================
# 3. ฟังก์ชันจัดการฐานข้อมูล (DATABASE)
# ==========================================
def load_data():
    """โหลดข้อมูลจากไฟล์ CSV เข้าสู่ Session State"""
    # 1. โหลดข้อมูลลูกค้า
    if "db_customers" not in st.session_state:
        if os.path.exists(CUST_FILE):
            try:
                df = pd.read_csv(CUST_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in df.columns: df = df.drop(columns=['Unnamed: 0'])
                st.session_state.db_customers = df
            except:
                st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
    
    # ตรวจสอบคอลัมน์ 'ลบ'
    if 'ลบ' not in st.session_state.db_customers.columns:
        st.session_state.db_customers.insert(0, 'ลบ', False)
    st.session_state.db_customers['ลบ'] = st.session_state.db_customers['ลบ'].fillna(False).astype(bool)

    # 2. โหลดข้อมูลสินค้า
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                df = pd.read_csv(PROD_FILE, encoding='utf-8-sig')
                # แปลงรหัสสินค้าเป็น String เสมอ
                df['รหัสสินค้า'] = df['รหัสสินค้า'].astype(str)
                if 'Unnamed: 0' in df.columns: df = df.drop(columns=['Unnamed: 0'])
                st.session_state.db_products = df
            except:
                st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])

    if 'ลบ' not in st.session_state.db_products.columns:
        st.session_state.db_products.insert(0, 'ลบ', False)
    st.session_state.db_products['ลบ'] = st.session_state.db_products['ลบ'].fillna(False).astype(bool)

    # 3. โหลดประวัติ
    if "db_history" not in st.session_state:
        if os.path.exists(HISTORY_FILE):
            try:
                df = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
                if 'ลบ' not in df.columns: df.insert(0, 'ลบ', False)
                if 'Unnamed: 0' in df.columns: df = df.drop(columns=['Unnamed: 0'])
                st.session_state.db_history = df
            except:
                st.session_state.db_history = pd.DataFrame(columns=["ลบ", "timestamp", "doc_no", "customer", "total", "data_json"])
        else:
            st.session_state.db_history = pd.DataFrame(columns=["ลบ", "timestamp", "doc_no", "customer", "total", "data_json"])

def save_data(df, filename, key_column=None):
    """บันทึก DataFrame ลงไฟล์ CSV โดยกรองแถวว่างออก"""
    df_to_save = df.copy()
    
    # กรองข้อมูลว่างทิ้ง เพื่อไม่ให้ไฟล์บวม
    if key_column and key_column in df_to_save.columns:
        df_to_save = df_to_save[df_to_save[key_column].astype(str).str.strip() != ""]
        
    df_to_save.to_csv(filename, index=False, encoding='utf-8-sig')

def to_num(val):
    """แปลงค่าเป็นตัวเลข ป้องกัน Error"""
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val) if val is not None else 0.0
    except:
        return 0.0

# เรียกใช้งานฟังก์ชันโหลดข้อมูลทันทีที่เปิดแอพ
load_data()

# ==========================================
# 4. ฟังก์ชันสร้าง PDF (FULL ENGINE)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    # ใช้ A4 หน่วยเป็น mm
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False) # ควบคุมหน้าเอง
    pdf.add_page()
    
    # --- จัดการฟอนต์ไทย ---
    if os.path.exists(FONT_PATH):
        try:
            # ลองเพิ่มฟอนต์แบบปกติ (สำหรับ fpdf เวอร์ชั่นทั่วไป)
            pdf.add_font('THSarabun', '', FONT_PATH, uni=True)
            pdf.add_font('THSarabun', 'B', FONT_PATH, uni=True)
            font_name = 'THSarabun'
        except:
            # Fallback (ถ้า library เวอร์ชั่นเก่า)
            pdf.add_font('THSarabun', '', FONT_PATH)
            pdf.add_font('THSarabun', 'B', FONT_PATH)
            font_name = 'THSarabun'
    else:
        # กรณีไม่มีฟอนต์เลย
        font_name = 'Arial' 
    
    # --- 1. ส่วนหัว (Header) ---
    # โลโก้ (ถ้ามี)
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=15, y=10, w=25)
            break
            
    # ข้อมูลบริษัทเรา
    pdf.set_xy(45, 10)
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 8, f"{d['my_comp']}", 0, 1, 'L')
    
    pdf.set_x(45)
    pdf.set_font(font_name, '', 12)
    pdf.multi_cell(100, 5, f"{d['my_addr']}\nโทร: {d['my_tel']} แฟกซ์: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # กรอบเลขที่เอกสาร (มุมขวาบน)
    pdf.set_xy(140, 10)
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(55, 18, "", 1, 0) # กรอบสี่เหลี่ยม
    
    pdf.set_xy(142, 12)
    pdf.cell(50, 6, f"เลขที่: {d['doc_no']}", 0, 1, 'L')
    pdf.set_x(142)
    pdf.cell(50, 6, f"วันที่: {d['doc_date']}", 0, 1, 'L')

    # ชื่อเอกสาร
    pdf.set_y(40)
    pdf.set_font(font_name, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # --- 2. ข้อมูลลูกค้าและเงื่อนไข ---
    pdf.set_y(55)
    start_y = pdf.get_y()
    
    # ลูกค้า (ซ้าย)
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(20, 6, "ลูกค้า:", 0, 0)
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, f"{d['c_name']}", 0, 1)
    
    pdf.set_x(15)
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(20, 6, "ผู้ติดต่อ:", 0, 0)
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, f"{d['contact']}", 0, 1)
    
    pdf.set_x(15)
    pdf.multi_cell(110, 5, f"ที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']} แฟกซ์: {d['c_fax']}", 0, 'L')
    
    # เงื่อนไข (ขวา)
    pdf.set_xy(130, start_y)
    pdf.multi_cell(65, 6, 
        f"กำหนดส่ง: {d['due_date']}\n"
        f"ยืนราคา: {d['valid_days']} วัน\n"
        f"เครดิต: {d['credit']} วัน\n"
        f"ครบกำหนด: {d['exp_date']}", 
        0, 'L')

    # --- 3. ตารางสินค้า ---
    pdf.set_y(85)
    
    # หัวตาราง
    cols_w = [12, 78, 15, 15, 25, 15, 25] # รวม 185 (A4 กว้าง 210 - margin 30)
    headers = ["ลำดับ", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_name, 'B', 11)
    for i, h in enumerate(headers):
        pdf.cell(cols_w[i], 8, h, 1, 0, 'C', True)
    pdf.ln()

    # ข้อมูลสินค้า
    pdf.set_font(font_name, '', 11)
    row_height = 7
    
    for i, row in items_df.iterrows():
        # ข้ามแถวว่าง
        if str(row.get('รายการ','')).strip() == "":
            continue
            
        # คำนวณค่าเพื่อแสดงผล
        q = to_num(row.get('จำนวน'))
        p = to_num(row.get('ราคา'))
        dis = to_num(row.get('ส่วนลด'))
        total_line = (q * p) - dis
        
        vals = [
            str(i+1),
            str(row.get('รายการ','')),
            f"{q:,.0f}",
            str(row.get('หน่วย','')),
            f"{p:,.2f}",
            f"{dis:,.2f}" if dis > 0 else "-",
            f"{total_line:,.2f}"
        ]
        
        # วาด Cell
        for j, txt in enumerate(vals):
            align = 'C'
            if j == 1: align = 'L' # รายการชิดซ้าย
            if j >= 4: align = 'R' # ตัวเลขชิดขวา
            pdf.cell(cols_w[j], row_height, txt, 1, 0, align)
        pdf.ln()

    # --- 4. สรุปยอดเงินและท้ายกระดาษ ---
    pdf.ln(3)
    current_y = pdf.get_y()
    
    # หมายเหตุ (ซ้าย)
    pdf.set_xy(15, current_y)
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(0, 6, "หมายเหตุ / Remarks:", 0, 1)
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(110, 5, remark_text, 0, 'L')
    
    # ยอดรวม (ขวา)
    # ตั้งค่าตำแหน่งเริ่มต้นของกล่องสรุป
    sum_x_label = 135
    sum_x_val = 175
    sum_y = current_y
    
    def print_sum_row(label, value, bold=False, line=False):
        nonlocal sum_y
        pdf.set_xy(sum_x_label, sum_y)
        pdf.set_font(font_name, 'B' if bold else '', 12)
        pdf.cell(40, 6, label, 0, 0, 'R')
        
        pdf.set_xy(sum_x_val, sum_y)
        pdf.cell(25, 6, f"{value:,.2f}", 'B' if line else 0, 1, 'R')
        sum_y += 6

    print_sum_row("รวมเงินสินค้า:", summary['gross'])
    print_sum_row("หักส่วนลด:", summary['discount'])
    print_sum_row("ยอดหลังหักส่วนลด:", summary['subtotal'])
    
    if show_vat_line:
        print_sum_row("ภาษีมูลค่าเพิ่ม 7%:", summary['vat'])
        
    print_sum_row("ยอดรวมทั้งสิ้น:", summary['grand_total'], True, True)

    # --- 5. ลายเซ็น ---
    # ไปที่ด้านล่างสุดของหน้า
    pdf.set_y(-45)
    pdf.set_font(font_name, '', 11)
    
    sig_labels = ["ผู้สั่งซื้อสินค้า", "พนักงานขาย", "ผู้อนุมัติ"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    
    x_positions = [20, 85, 150] # ตำแหน่งแกน X ของ 3 คน
    y_sig = pdf.get_y()
    
    for i in range(3):
        pdf.set_xy(x_positions[i], y_sig)
        pdf.cell(40, 5, "........................................", 0, 1, 'C') # เส้นเซ็น
        
        pdf.set_xy(x_positions[i], y_sig + 5)
        pdf.cell(40, 5, sig_labels[i], 0, 1, 'C') # ตำแหน่ง
        
        pdf.set_xy(x_positions[i], y_sig + 10)
        display_name = f"({names[i]})" if names[i] else "(........................................)"
        pdf.cell(40, 5, display_name, 0, 1, 'C') # ชื่อวงเล็บ

    return bytes(pdf.output())

# ==========================================
# 5. ส่วนแสดงผล (USER INTERFACE)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า", "🗂️ ประวัติเอกสาร"])

# ------------------------------------------------------------------
# TAB 1: หน้าสร้างเอกสาร (Quotation)
# ------------------------------------------------------------------
with tab1:
    # --- ส่วนที่ 1: ข้อมูลบริษัทเราและเอกสาร ---
    with st.container(border=True):
        st.subheader("📋 ข้อมูลเอกสาร")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.text_input("ชื่อบริษัทผู้ขาย", "บริษัท ตัวอย่าง จำกัด", key="my_comp_in")
            st.text_input("ที่อยู่บริษัท", "123 ถนนตัวอย่าง กทม.", key="my_addr_in")
            
            c1, c2, c3 = st.columns(3)
            with c1: st.text_input("โทรศัพท์", key="my_tel_in")
            with c2: st.text_input("แฟกซ์", key="my_fax_in")
            with c3: st.text_input("เลขผู้เสียภาษี", key="my_tax_in")
            
        with col_b:
            # ใช้ f-string สร้างเลขที่เอกสารอัตโนมัติ
            auto_doc = f"QT-{datetime.now().strftime('%Y%m%d')}-001"
            st.text_input("เลขที่ใบเสนอราคา", value=auto_doc, key="doc_no_in")
            
            # ใช้ Date Input เพื่อความแม่นยำ
            st.date_input("วันที่ออกเอกสาร", date.today(), key="doc_date_in")
            
            st.text_input("กำหนดส่งของ", "ภายใน 7-15 วัน", key="due_date_in")
            
            r1, r2 = st.columns(2)
            with r1: st.number_input("ยืนราคา (วัน)", min_value=1, value=30, key="valid_days_in")
            with r2: st.number_input("เครดิต (วัน)", min_value=0, value=30, key="credit_in")

    st.write("---")

    # --- ส่วนที่ 2: ข้อมูลลูกค้า ---
    with st.container(border=True):
        head_c1, head_c2 = st.columns([1, 1])
        with head_c1: st.subheader("👤 ข้อมูลลูกค้า")
        
        # Dropdown เลือกจากฐานข้อมูล
        cust_options = ["-- พิมพ์เอง --"] + st.session_state.db_customers['ชื่อบริษัท'].dropna().tolist()
        
        def on_cust_select():
            """Callback เมื่อเลือกลูกค้า ให้เติมคำลงช่องว่าง"""
            selected = st.session_state.cust_selector_tab1
            if selected and selected != "-- พิมพ์เอง --":
                # หาข้อมูลใน DB
                found = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == selected]
                if not found.empty:
                    row = found.iloc[0]
                    st.session_state.c_name_in = str(row['ชื่อบริษัท'])
                    st.session_state.contact_in = str(row['ผู้ติดต่อ']) if pd.notna(row['ผู้ติดต่อ']) else ""
                    st.session_state.c_addr_in = str(row['ที่อยู่']) if pd.notna(row['ที่อยู่']) else ""
                    st.session_state.c_tel_in = str(row['โทร']) if pd.notna(row['โทร']) else ""
                    st.session_state.c_fax_in = str(row['แฟกซ์']) if pd.notna(row['แฟกซ์']) else ""

        with head_c2:
            st.selectbox("ค้นหาลูกค้าเก่า", cust_options, key="cust_selector_tab1", on_change=on_cust_select)

        cc1, cc2 = st.columns(2)
        with cc1:
            st.text_input("ชื่อบริษัทลูกค้า", key="c_name_in")
            st.text_input("ชื่อผู้ติดต่อ", key="contact_in")
            st.text_area("ที่อยู่จัดส่ง/ออกใบกำกับ", height=85, key="c_addr_in")
        with cc2:
            st.text_input("เบอร์โทรศัพท์", key="c_tel_in")
            st.text_input("เบอร์แฟกซ์", key="c_fax_in")

    st.write("---")

    # --- ส่วนที่ 3: ตารางสินค้า (Grid) ---
    st.subheader("📦 รายการสินค้า")
    
    # ดึงรหัสสินค้ามาทำ Dropdown ในตาราง
    product_codes = st.session_state.db_products['รหัสสินค้า'].astype(str).tolist()
    
    # แสดงตารางแบบแก้ไขได้ (Data Editor)
    edited_df = st.data_editor(
        st.session_state.grid_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัสสินค้า", options=product_codes, required=False, width="medium"),
            "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
            "จำนวน": st.column_config.NumberColumn("จำนวน", min_value=0.0, format="%.2f"),
            "หน่วย": st.column_config.TextColumn("หน่วยนับ", width="small"),
            "ราคา": st.column_config.NumberColumn("ราคา/หน่วย", min_value=0.0, format="%.2f"),
            "ส่วนลด": st.column_config.NumberColumn("ส่วนลด (บาท)", min_value=0.0, format="%.2f")
        },
        num_rows="dynamic", # เพิ่มลบแถวได้
        use_container_width=True,
        key="main_quotation_editor"
    )

    # --- Logic Auto-Fill สินค้า (เมื่อเลือกรหัสสินค้า ให้เติมชื่อและราคา) ---
    needs_rerun = False
    for idx, row in edited_df.iterrows():
        code = str(row['รหัสสินค้า'])
        # ถ้ามีรหัสสินค้า และยังไม่มีชื่อรายการ (หรือชื่อรายการไม่ตรงกับ DB)
        if code and code in product_codes:
            prod_info = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'] == code].iloc[0]
            
            # ตรวจสอบว่าต้องอัปเดตหรือไม่ (ป้องกัน Loop)
            if str(row['รายการ']) == "" or str(row['รายการ']) != prod_info['รายการ']:
                edited_df.at[idx, 'รายการ'] = prod_info['รายการ']
                edited_df.at[idx, 'ราคา'] = float(prod_info['ราคา'])
                edited_df.at[idx, 'หน่วย'] = prod_info['หน่วย']
                needs_rerun = True
    
    if needs_rerun:
        st.session_state.grid_df = edited_df
        st.rerun()
    else:
        st.session_state.grid_df = edited_df

    # --- ส่วนที่ 4: การคำนวณเงิน (Real-time Calculation) ---
    # สร้าง Dataframe สำหรับคำนวณแยกออกมา เพื่อไม่ให้กระทบตารางหลัก
    calc_df = edited_df.copy()
    calc_df['q'] = calc_df['จำนวน'].apply(to_num)
    calc_df['p'] = calc_df['ราคา'].apply(to_num)
    calc_df['d'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['total_line'] = (calc_df['q'] * calc_df['p']) - calc_df['d']

    sum_gross = (calc_df['q'] * calc_df['p']).sum()
    sum_discount = calc_df['d'].sum()
    sum_subtotal = calc_df['total_line'].sum()

    st.write("---")

    # --- ส่วนที่ 5: สรุปท้ายใบเสนอราคา ---
    footer_col1, footer_col2 = st.columns([1.5, 1])
    
    with footer_col1:
        st.text_area("หมายเหตุ / เงื่อนไขการชำระเงิน", 
                     value="1. ราคาดังกล่าวยังไม่รวมภาษีมูลค่าเพิ่ม 7%\n2. กำหนดยืนราคา 30 วัน", 
                     height=120, key="remark_in")
        
        st.caption("ข้อมูลผู้ลงนาม (Optional)")
        sig1, sig2, sig3 = st.columns(3)
        with sig1: st.text_input("ผู้สั่งซื้อ (ลูกค้า)", key="s1_in")
        with sig2: st.text_input("พนักงานขาย", key="s2_in")
        with sig3: st.text_input("ผู้อนุมัติ", key="s3_in")
        
    with footer_col2:
        # Checkbox ภาษี
        has_vat = st.checkbox("คำนวณภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)
        
        vat_amount = sum_subtotal * 0.07 if has_vat else 0.0
        grand_total = sum_subtotal + vat_amount
        
        # แสดงผลลัพธ์แบบ Card สวยงาม
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">ยอดรวมทั้งสิ้น (Grand Total)</div>
            <div class="metric-value">{grand_total:,.2f} บาท</div>
            <div class="metric-sub">
                รวมสินค้า: {sum_gross:,.2f}<br>
                ส่วนลด: -{sum_discount:,.2f}<br>
                ยอดก่อน VAT: {sum_subtotal:,.2f}<br>
                VAT 7%: {vat_amount:,.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("###") # เว้นบรรทัด

    # --- ปุ่มดำเนินการ (Action Buttons) ---
    act_col1, act_col2, act_col3 = st.columns([1, 2, 2])
    
    with act_col1:
        if st.button("🗑️ ล้างหน้าจอ", use_container_width=True):
            # Reset ค่าทั้งหมด
            for k in default_keys:
                st.session_state[k] = ""
            st.session_state.grid_df = pd.DataFrame([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0.0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 15)
            st.rerun()

    with act_col3:
        if st.button("💾 บันทึกและพิมพ์ PDF", type="primary", use_container_width=True):
            # 1. ตรวจสอบเลขที่เอกสารซ้ำ
            doc_no = st.session_state.doc_no_in
            if not st.session_state.db_history.empty and doc_no in st.session_state.db_history['doc_no'].values:
                st.warning(f"⚠️ เลขที่ {doc_no} มีอยู่ในระบบแล้ว จะเป็นการบันทึกซ้ำ")
            
            # 2. เตรียมข้อมูลบันทึกประวัติ (JSON)
            history_json = {
                "grid_df": edited_df.to_dict(),
                "c_name": st.session_state.c_name_in,
                "contact": st.session_state.contact_in,
                "c_addr": st.session_state.c_addr_in,
                "c_tel": st.session_state.c_tel_in,
                "remark": st.session_state.remark_in,
                "doc_date_str": str(st.session_state.doc_date_in), # เก็บเป็น String
                "grand_total": grand_total
            }
            
            new_record = {
                "ลบ": False,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "doc_no": doc_no,
                "customer": st.session_state.c_name_in,
                "total": grand_total,
                "data_json": json.dumps(history_json, ensure_ascii=False)
            }
            
            # บันทึกลง DataFrame และ CSV
            record_df = pd.DataFrame([new_record])
            st.session_state.db_history = pd.concat([record_df, st.session_state.db_history], ignore_index=True)
            save_data(st.session_state.db_history, HISTORY_FILE)
            
            # 3. สร้าง PDF
            pdf_info = {
                "my_comp": st.session_state.my_comp_in, "my_addr": st.session_state.my_addr_in,
                "my_tel": st.session_state.my_tel_in, "my_fax": st.session_state.my_fax_in, "my_tax": st.session_state.my_tax_in,
                "doc_no": doc_no, "doc_date": st.session_state.doc_date_in.strftime("%d/%m/%Y"),
                "due_date": st.session_state.due_date_in,
                "valid_days": st.session_state.valid_days_in,
                "credit": st.session_state.credit_in,
                # คำนวณวันหมดอายุอัตโนมัติ
                "exp_date": (st.session_state.doc_date_in + timedelta(days=int(st.session_state.valid_days_in))).strftime("%d/%m/%Y"),
                "c_name": st.session_state.c_name_in, "contact": st.session_state.contact_in,
                "c_addr": st.session_state.c_addr_in, "c_tel": st.session_state.c_tel_in, "c_fax": st.session_state.c_fax_in
            }
            
            summary_info = {
                "gross": sum_gross, "discount": sum_discount, 
                "subtotal": sum_subtotal, "vat": vat_amount, "grand_total": grand_total
            }
            
            sigs_info = {
                "s1": st.session_state.s1_in, "s2": st.session_state.s2_in, "s3": st.session_state.s3_in
            }
            
            # เรียกฟังก์ชัน PDF
            pdf_bytes = create_pdf(pdf_info, calc_df, summary_info, sigs_info, st.session_state.remark_in, has_vat)
            
            st.success("✅ บันทึกข้อมูลและสร้างไฟล์สำเร็จ!")
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์ PDF",
                data=pdf_bytes,
                file_name=f"{doc_no}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ------------------------------------------------------------------
# TAB 2: ฐานข้อมูลลูกค้า (Customers)
# ------------------------------------------------------------------
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    st.info("💡 วิธีลบ: ติ๊กช่อง 'ลบ' หน้าชื่อที่ต้องการ แล้วกดปุ่มบันทึกสีแดงด้านล่าง")
    
    # Editor
    edited_customers = st.data_editor(
        st.session_state.db_customers,
        column_config={
            "ลบ": st.column_config.CheckboxColumn("ลบรายการ", default=False, width="small"),
            "รหัส": st.column_config.TextColumn("รหัส", width="small"),
            "ชื่อบริษัท": st.column_config.TextColumn("ชื่อบริษัท", width="large", required=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="customer_editor"
    )
    
    # ปุ่มบันทึก (จัดการการลบและบันทึกในปุ่มเดียว)
    if st.button("💾 บันทึกการเปลี่ยนแปลง (ลูกค้า)", type="primary"):
        # 1. กรองเอาเฉพาะแถวที่ไม่ได้ติ๊ก 'ลบ'
        active_customers = edited_customers[edited_customers['ลบ'] == False].copy()
        
        # 2. Reset Index ให้เรียงใหม่
        active_customers = active_customers.reset_index(drop=True)
        
        # 3. อัปเดต State และ Save ลงไฟล์
        st.session_state.db_customers = active_customers
        save_data(active_customers, CUST_FILE, key_column="ชื่อบริษัท")
        
        st.toast("✅ บันทึกข้อมูลลูกค้าเรียบร้อย", icon="💾")
        st.rerun()

# ------------------------------------------------------------------
# TAB 3: ฐานข้อมูลสินค้า (Products)
# ------------------------------------------------------------------
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    st.info("💡 วิธีลบ: ติ๊กช่อง 'ลบ' หน้าสินค้าที่ต้องการ แล้วกดปุ่มบันทึกสีแดงด้านล่าง")
    
    # Editor
    edited_products = st.data_editor(
        st.session_state.db_products,
        column_config={
            "ลบ": st.column_config.CheckboxColumn("ลบรายการ", default=False, width="small"),
            "รหัสสินค้า": st.column_config.TextColumn("รหัสสินค้า", width="small", required=True),
            "รายการ": st.column_config.TextColumn("ชื่อสินค้า", width="large"),
            "ราคา": st.column_config.NumberColumn("ราคาขาย", format="%.2f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="product_editor"
    )
    
    # ปุ่มบันทึก (Logic เดียวกับลูกค้า)
    if st.button("💾 บันทึกการเปลี่ยนแปลง (สินค้า)", type="primary"):
        # 1. กรองเอาเฉพาะแถวที่ไม่ได้ติ๊ก 'ลบ'
        active_products = edited_products[edited_products['ลบ'] == False].copy()
        
        # 2. Reset Index
        active_products = active_products.reset_index(drop=True)
        
        # 3. อัปเดต State และ Save
        st.session_state.db_products = active_products
        save_data(active_products, PROD_FILE, key_column="รหัสสินค้า")
        
        st.toast("✅ บันทึกข้อมูลสินค้าเรียบร้อย", icon="💾")
        st.rerun()

# ------------------------------------------------------------------
# TAB 4: ประวัติเอกสาร (History)
# ------------------------------------------------------------------
with tab4:
    st.header("🗂️ ประวัติใบเสนอราคา")
    
    if st.session_state.db_history.empty:
        st.warning("ยังไม่มีประวัติเอกสาร")
    else:
        # ส่วนเลือกโหลดข้อมูล
        col_sel1, col_sel2 = st.columns([3, 1])
        with col_sel1:
            history_list = st.session_state.db_history['doc_no'].tolist()
            selected_history_doc = st.selectbox("เลือกเลขที่เอกสารเพื่อดูหรือแก้ไข", history_list)
        
        with col_sel2:
            st.write("") # ดันปุ่มลงมา
            st.write("")
            if st.button("🔄 โหลดข้อมูลกลับหน้าแรก", use_container_width=True):
                # ค้นหาข้อมูลจากเลขที่
                hist_row = st.session_state.db_history[st.session_state.db_history['doc_no'] == selected_history_doc].iloc[0]
                
                try:
                    # Parse JSON กลับมา
                    saved_data = json.loads(hist_row['data_json'])
                    
                    # 1. คืนค่าตารางสินค้า
                    st.session_state.grid_df = pd.DataFrame.from_dict(saved_data['grid_df'])
                    
                    # 2. คืนค่าข้อมูล Input Fields
                    st.session_state.c_name_in = saved_data.get('c_name', '')
                    st.session_state.contact_in = saved_data.get('contact', '')
                    st.session_state.c_addr_in = saved_data.get('c_addr', '')
                    st.session_state.c_tel_in = saved_data.get('c_tel', '')
                    st.session_state.remark_in = saved_data.get('remark', '')
                    st.session_state.doc_no_in = hist_row['doc_no']
                    
                    # แปลงวันที่จาก String กลับเป็น Date Object
                    if 'doc_date_str' in saved_data:
                        try:
                            st.session_state.doc_date_in = datetime.strptime(saved_data['doc_date_str'], '%Y-%m-%d').date()
                        except: pass
                        
                    st.toast(f"✅ โหลดข้อมูล {selected_history_doc} เรียบร้อย! กรุณากลับไปที่ Tab 1", icon="🔄")
                
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ประวัติ: {e}")

        st.divider()
        
        # ตารางแสดงประวัติแบบแก้ไขได้ (เพื่อลบประวัติ)
        edited_history = st.data_editor(
            st.session_state.db_history,
            column_config={
                "ลบ": st.column_config.CheckboxColumn("ลบ", default=False),
                "timestamp": st.column_config.TextColumn("วัน-เวลาที่บันทึก", disabled=True),
                "doc_no": st.column_config.TextColumn("เลขที่", disabled=True),
                "customer": st.column_config.TextColumn("ลูกค้า", disabled=True),
                "total": st.column_config.NumberColumn("ยอดรวม", format="%.2f", disabled=True),
                "data_json": None # ซ่อนคอลัมน์ JSON ไม่ให้รก
            },
            use_container_width=True,
            hide_index=True,
            key="history_editor"
        )
        
        if st.button("💾 อัปเดตประวัติ (ลบรายการที่เลือก)", type="primary"):
             # Logic การลบเหมือน Tab อื่น
            active_history = edited_history[edited_history['ลบ'] == False].copy()
            active_history = active_history.reset_index(drop=True)
            
            st.session_state.db_history = active_history
            save_data(active_history, HISTORY_FILE)
            
            st.toast("✅ ลบประวัติที่เลือกเรียบร้อย", icon="🗑️")
            st.rerun()
