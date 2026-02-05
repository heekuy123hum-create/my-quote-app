import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF
import json

# ==========================================
# 1. DATABASE SYSTEM & CONFIGURATION
# ==========================================
st.set_page_config(page_title="SIWAKIT TRADING SYSTEM", layout="wide", page_icon="🏢")

# ชื่อไฟล์สำหรับเก็บข้อมูลต่างๆ
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"
HISTORY_FILE = "history_quotes.csv"

# เริ่มต้นตัวแปร Session State หากยังไม่มี
if "grid_df" not in st.session_state:
    # สร้างตารางเปล่า 20 บรรทัด สำหรับรายการสินค้า
    st.session_state.grid_df = pd.DataFrame(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 20
    )

# ==========================================
# 2. ฟังก์ชันจัดการข้อมูล (LOAD & SAVE)
# ==========================================
def load_data():
    # --- 1. โหลดข้อมูลลูกค้า ---
    if "db_customers" not in st.session_state:
        if os.path.exists(CUST_FILE):
            try:
                temp_df = pd.read_csv(CUST_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df.columns: 
                    temp_df = temp_df.drop(columns=['Unnamed: 0'])
                if 'รหัส' in temp_df.columns:
                    temp_df['รหัส'] = temp_df['รหัส'].astype(str)
                st.session_state.db_customers = temp_df
            except:
                st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            st.session_state.db_customers = pd.DataFrame([
                {"ลบ": False, "รหัส": "C001", "ชื่อบริษัท": "บริษัท ตัวอย่าง จำกัด", "ผู้ติดต่อ": "คุณสมชาย", "ที่อยู่": "123 กทม.", "โทร": "081-111-1111", "แฟกซ์": "02-222-2222"},
                {"ลบ": False, "รหัส": "C002", "ชื่อบริษัท": "หจก. ทดสอบระบบ", "ผู้ติดต่อ": "คุณสมหญิง", "ที่อยู่": "456 เชียงใหม่", "โทร": "089-999-9999", "แฟกซ์": "-"}
            ])
        
        if 'ลบ' not in st.session_state.db_customers.columns:
            st.session_state.db_customers.insert(0, 'ลบ', False)

    # --- 2. โหลดข้อมูลสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                temp_df_p = pd.read_csv(PROD_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df_p.columns: 
                    temp_df_p = temp_df_p.drop(columns=['Unnamed: 0'])
                if 'รหัสสินค้า' in temp_df_p.columns:
                    temp_df_p['รหัสสินค้า'] = temp_df_p['รหัสสินค้า'].astype(str)
                st.session_state.db_products = temp_df_p
            except:
                st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            st.session_state.db_products = pd.DataFrame([
                {"ลบ": False, "รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง A", "ราคา": 1500.0, "หน่วย": "ชิ้น"},
                {"ลบ": False, "รหัสสินค้า": "P002", "รายการ": "สินค้าตัวอย่าง B", "ราคา": 2500.0, "หน่วย": "เครื่อง"},
                {"ลบ": False, "รหัสสินค้า": "P003", "รายการ": "ค่าบริการติดตั้ง", "ราคา": 5000.0, "หน่วย": "งาน"}
            ])
        
        if 'ลบ' not in st.session_state.db_products.columns:
            st.session_state.db_products.insert(0, 'ลบ', False)

    # --- 3. โหลดประวัติใบเสนอราคา ---
    if "db_history" not in st.session_state:
        if os.path.exists(HISTORY_FILE):
            try:
                st.session_state.db_history = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
            except:
                 st.session_state.db_history = pd.DataFrame(columns=["timestamp", "doc_no", "customer", "total", "data_json"])
        else:
            st.session_state.db_history = pd.DataFrame(columns=["timestamp", "doc_no", "customer", "total", "data_json"])

def save_data(df, filename):
    """ฟังก์ชันบันทึก Dataframe ลง CSV ตัดคอลัมน์ที่ไม่จำเป็นออก"""
    df_to_save = df.copy()
    if 'ลบ' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['ลบ'])
    if 'Unnamed: 0' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['Unnamed: 0'])
    df_to_save.to_csv(filename, index=False, encoding='utf-8-sig')

def to_num(val):
    """ฟังก์ชันแปลงข้อความตัวเลขที่มีลูกน้ำ เป็น float"""
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val) if val else 0.0
    except:
        return 0.0

# เรียกใช้ฟังก์ชันโหลดข้อมูลทันที
load_data()

# ==========================================
# 3. PDF ENGINE
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # Font Logic
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path, uni=True)
        pdf.add_font('THSarabun', 'B', font_path, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # Logo
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
            
    # Header Left
    pdf.set_xy(35, 10)
    pdf.set_font(use_f, 'B', 14)
    header_text = f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}"
    pdf.multi_cell(100, 6, header_text, 0, 'L')

    # Header Right
    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0)
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    # Title
    pdf.set_y(42)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # Customer & Terms
    pdf.set_font(use_f, '', 14)
    pdf.ln(2)
    start_info_y = pdf.get_y()
    
    pdf.set_xy(10, start_info_y)
    cust_info = f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}"
    pdf.multi_cell(115, 6, cust_info, 0, 'L')
    y_left = pdf.get_y()
    
    pdf.set_xy(130, start_info_y)
    terms_info = f"วันที่กำหนดส่ง: {d['due_date']}\nยืนราคา (วัน): {d['valid_days']}  Expire Date: {d['exp_date']}\nเครดิต (วัน): {d['credit']}"
    pdf.multi_cell(75, 6, terms_info, 0, 'L')
    y_right = pdf.get_y()
    
    pdf.set_y(max(y_left, y_right) + 5)

    # Table
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 11)
    
    w = [15, 75, 15, 15, 25, 15, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 11)
    row_height = 6.0
    
    for i in range(20):
        if i < len(items_df):
            row = items_df.iloc[i]
            if str(row.get('รายการ','')).strip() != "":
                vals = [
                    str(row.get('รหัสสินค้า','')),
                    str(row.get('รายการ','')),
                    f"{to_num(row.get('จำนวน')):,.0f}",
                    str(row.get('หน่วย','')),
                    f"{to_num(row.get('ราคา')):,.0f}",
                    f"{to_num(row.get('ส่วนลด')):,.0f}",
                    f"{to_num(row.get('รวมเงิน',0)):,.0f}"
                ]
            else:
                vals = [""] * 7
        else:
            vals = [""] * 7
            
        for j in range(7):
            align = 'L' if j == 1 else 'C'
            if j == 6: align = 'R'
            pdf.cell(w[j], row_height, vals[j], 1, 0, align)
        pdf.ln()

    pdf.ln(2)
    footer_y = pdf.get_y()
    
    # Remarks
    pdf.set_xy(10, footer_y)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12)
    pdf.set_x(10)
    pdf.multi_cell(105, 5, remark_text, 0, 'L')
    
    # Totals
    curr_y = footer_y
    label_x = 125
    val_x = 175

    def add_total_row(label, value, is_bold=False, is_red=False):
        nonlocal curr_y
        pdf.set_font(use_f, 'B' if is_bold else '', 13 if is_bold else 12)
        if is_red: pdf.set_text_color(180, 0, 0)
        else: pdf.set_text_color(0, 0, 0)
        
        pdf.set_xy(label_x, curr_y)
        pdf.cell(45, 5.5, label, 0, 0, 'R')
        pdf.set_xy(val_x, curr_y)
        pdf.cell(25, 5.5, f"{value:,.2f}", 'B', 1, 'R')
        curr_y += 5.5

    add_total_row("รวมเงินย่อย (Gross Total):", summary['gross'])
    add_total_row("ส่วนลด (Total Discount):", summary['discount'])
    add_total_row("หลังหักส่วนลด (Sub Total):", summary['subtotal'])
    
    if show_vat_line:
        add_total_row("ภาษีมูลค่าเพิ่ม (VAT 7%):", summary['vat'])
        
    add_total_row("ยอดรวมทั้งสิ้น (Grand Total):", summary['grand_total'], True, True)

    # Signatures
    pdf.set_y(-35)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(use_f, '', 11)
    
    sig_titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    sig_names = [sigs['s1'], sigs['s2'], sigs['s3']]
    sig_x = [10, 75, 140]
    sig_y = pdf.get_y()
    
    for i in range(3):
        pdf.set_xy(sig_x[i], sig_y)
        pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_xy(sig_x[i], sig_y + 5)
        pdf.cell(60, 5, sig_titles[i], 0, 1, 'C')
        pdf.set_xy(sig_x[i], sig_y + 10)
        pdf.cell(60, 5, f"({sig_names[i]})" if sig_names[i] else "(...................................................)", 0, 1, 'C')
        pdf.set_xy(sig_x[i], sig_y + 15)
        pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')

    return bytes(pdf.output())

# ==========================================
# 4. CALLBACK FUNCTIONS (แก้ปัญหา Error)
# ==========================================
def restore_history_callback():
    """ฟังก์ชัน Callback สำหรับโหลดข้อมูลประวัติ เพื่อป้องกัน StreamlitAPIException"""
    # ดึงค่า key ของเอกสารที่เลือกจาก session_state
    sel_doc = st.session_state.get("history_selector_box")
    
    if sel_doc:
        # ค้นหาข้อมูล JSON
        row_data = st.session_state.db_history[st.session_state.db_history['doc_no'] == sel_doc].iloc[0]
        saved_data = json.loads(row_data['data_json'])
        
        # คืนค่าตารางสินค้า
        st.session_state.grid_df = pd.DataFrame.from_dict(saved_data['grid_df'])
        
        # คืนค่าตัวแปรอื่นๆ ลง Session State (ใช้ Keys ที่ตรงกับ Widget)
        keys_map = {
            "doc_no_in": "doc_no", "doc_date_in": "doc_date", "due_date_in": "due_date",
            "valid_days_in": "valid_days", "credit_in": "credit", "exp_date_in": "exp_date",
            "c_name_in": "c_name", "contact_in": "contact", "c_addr_in": "c_addr", 
            "c_tel_in": "c_tel", "c_fax_in": "c_fax", "remark_in": "remark", 
            "has_vat_in": "has_vat", "s1_in": "s1", "s2_in": "s2", "s3_in": "s3"
        }
        
        for key_ss, key_json in keys_map.items():
            if key_json in saved_data:
                st.session_state[key_ss] = saved_data[key_json]
        
        st.toast(f"✅ โหลดข้อมูล {sel_doc} เรียบร้อย! กรุณากลับไปที่ Tab 1", icon="🔄")

# ==========================================
# 5. ส่วนแสดงผล (User Interface - Tab System)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า", "🗂️ ประวัติใบเสนอราคา"])

# ------------------------------------------------------------------
# TAB 1: หน้าสร้างใบเสนอราคา (Quotation)
# ------------------------------------------------------------------
with tab1:
    col1, col2 = st.columns(2)
    
    # ข้อมูลผู้เสนอราคา
    with col1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัท", "บริษัท ศิวกิจ เทรดดิ้ง จำกัด", key="my_comp_in")
        my_addr = st.text_input("ที่อยู่บริษัท", "", key="my_addr_in") 
        my_tel = st.text_input("โทรศัพท์", "", key="my_tel_in")      
        my_fax = st.text_input("โทรสาร", "", key="my_fax_in")        
        my_tax = st.text_input("เลขผู้เสียภาษี", "", key="my_tax_in")
    
    # รายละเอียดเอกสาร
    with col2:
        st.subheader("📄 รายละเอียดเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d')}-001", key="doc_no_in")
        doc_date = st.text_input("วันที่ออกเอกสาร", datetime.now().strftime('%d/%m/%Y'), key="doc_date_in")
        due_date = st.text_input("วันที่กำหนดส่ง", "7 วัน", key="due_date_in")
        
        v_col1, v_col2 = st.columns(2)
        valid_days = v_col1.text_input("ยืนราคา (วัน)", "30", key="valid_days_in")
        exp_date = v_col2.text_input("Expire Date", datetime.now().strftime('%d/%m/%Y'), key="exp_date_in")
        credit = st.text_input("เครดิต (วัน)", "30", key="credit_in")

    st.divider()

    # ส่วนเลือกข้อมูลลูกค้า
    c_h1, c_h2 = st.columns([1, 1])
    with c_h1: st.subheader("👤 ข้อมูลลูกค้า")
    with c_h2: 
        # ดึงรายชื่อลูกค้าจาก Session State โดยตรง (เพื่อให้เห็นข้อมูลล่าสุดเสมอ)
        current_customers = st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist()
        c_list = ["-- พิมพ์เอง --"] + [str(x) for x in current_customers if str(x).strip() != ""]
        sel_c = st.selectbox("📥 ดึงข้อมูลลูกค้าเก่า", c_list, key="cust_selector_tab1")

    # Logic ดึงข้อมูลลูกค้า
    def_name, def_cont, def_addr, def_tel, def_fax = "", "", "", "", ""
    if sel_c != "-- พิมพ์เอง --":
        found_c = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == sel_c]
        if not found_c.empty:
            row_c = found_c.iloc[0]
            def_name, def_cont, def_addr, def_tel, def_fax = row_c['ชื่อบริษัท'], row_c['ผู้ติดต่อ'], row_c['ที่อยู่'], row_c['โทร'], row_c['แฟกซ์']

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        c_name = st.text_input("ชื่อบริษัทลูกค้า", value=def_name, key="c_name_in")
        contact = st.text_input("ชื่อผู้ติดต่อ", value=def_cont, key="contact_in")
        c_addr = st.text_area("ที่อยู่จัดส่ง/วางบิล", value=def_addr, height=70, key="c_addr_in")
    with c_col2:
        st.write("<br><br>", unsafe_allow_html=True) 
        c_tel = st.text_input("เบอร์โทรศัพท์ลูกค้า", value=def_tel, key="c_tel_in")
        c_fax = st.text_input("เบอร์แฟกซ์ลูกค้า", value=def_fax, key="c_fax_in")

    # ส่วนตารางรายการสินค้า
    st.subheader("📦 รายการสินค้า")
    
    current_products = st.session_state.db_products['รหัสสินค้า'].dropna().unique().tolist()
    p_codes = [str(x) for x in current_products if str(x).strip() != ""]
    
    current_df = st.session_state.grid_df.fillna(0)
    
    edited_df = st.data_editor(
        current_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัสสินค้า", options=p_codes, width="medium"),
            "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
            "จำนวน": st.column_config.NumberColumn("จำนวน", min_value=0, format="%.2f"),
            "ราคา": st.column_config.NumberColumn("ราคา/หน่วย", min_value=0, format="%.2f"),
            "ส่วนลด": st.column_config.NumberColumn("ส่วนลด", format="%.2f")
        },
        column_order=("รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา", "ส่วนลด"),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_main"
    )

    # Logic: Auto-fill ข้อมูลสินค้า
    needs_rerun = False
    for idx, row in edited_df.iterrows():
        code = str(row['รหัสสินค้า'])
        if code and code in p_codes:
            found_prod = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'].astype(str) == code]
            if not found_prod.empty:
                p_info = found_prod.iloc[0]
                if row['รายการ'] != p_info['รายการ']:
                    edited_df.at[idx, 'รายการ'] = p_info['รายการ']
                    edited_df.at[idx, 'หน่วย'] = p_info['หน่วย']
                    edited_df.at[idx, 'ราคา'] = p_info['ราคา']
                    needs_rerun = True

    if needs_rerun:
        st.session_state.grid_df = edited_df
        st.rerun()
    else:
        st.session_state.grid_df = edited_df

    # คำนวณยอดเงิน
    calc_df = edited_df.copy()
    calc_df['q'] = calc_df['จำนวน'].apply(to_num)
    calc_df['p'] = calc_df['ราคา'].apply(to_num)
    calc_df['d'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['รวมเงิน'] = (calc_df['q'] * calc_df['p']) - calc_df['d']
    
    sum_gross = (calc_df['q'] * calc_df['p']).sum()
    sum_disc = calc_df['d'].sum()
    sum_sub = calc_df['รวมเงิน'].sum()

    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        remark = st.text_area("📝 หมายเหตุ", value="1. สินค้ารับประกัน 1 ปี\n2. กำหนดยืนราคาตามที่ระบุในเอกสาร", key="remark_in")
    with f_col2:
        st.write("### สรุปยอดเงิน")
        has_vat = st.checkbox("✅ คิด VAT 7%", value=True, key="has_vat_in")
        vat_val = (sum_sub * 0.07) if has_vat else 0.0
        grand_total = sum_sub + vat_val

        st.write(f"รวมเป็นเงิน: {sum_gross:,.2f}")
        st.write(f"ส่วนลดทั้งหมด: -{sum_disc:,.2f}")
        st.write(f"ยอดหลังหักส่วนลด: {sum_sub:,.2f}")
        if has_vat:
            st.write(f"ภาษีมูลค่าเพิ่ม 7%: {vat_val:,.2f}")
        st.metric("ยอดรวมทั้งสิ้น", f"{grand_total:,.2f} บาท")

    s_col1, s_col2, s_col3 = st.columns(3)
    s1 = s_col1.text_input("ชื่อลูกค้า", key="s1_in")
    s2 = s_col2.text_input("ชื่อพนักงานขาย", key="s2_in")
    s3 = s_col3.text_input("ชื่อผู้จัดการ", key="s3_in")

    if st.button("🚀 สร้าง PDF + บันทึกประวัติ", type="primary", use_container_width=True):
        history_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "doc_no": doc_no,
            "customer": c_name,
            "total": grand_total,
            "data_json": json.dumps({
                "grid_df": edited_df.to_dict(),
                "doc_date": doc_date, "due_date": due_date, "valid_days": valid_days, "credit": credit, "exp_date": exp_date,
                "c_name": c_name, "contact": contact, "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax,
                "remark": remark, "has_vat": has_vat, "s1": s1, "s2": s2, "s3": s3
            }, ensure_ascii=False)
        }
        new_history = pd.DataFrame([history_data])
        st.session_state.db_history = pd.concat([new_history, st.session_state.db_history], ignore_index=True)
        save_data(st.session_state.db_history, HISTORY_FILE)
        st.toast("บันทึกประวัติเรียบร้อย!", icon="💾")

        d_pdf = {
            "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
            "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "valid_days": valid_days,
            "exp_date": exp_date, "credit": credit, "c_name": c_name, "contact": contact,
            "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax
        }
        res_pdf = create_pdf(
            d_pdf, calc_df, 
            {"gross": sum_gross, "discount": sum_disc, "subtotal": sum_sub, "vat": vat_val, "grand_total": grand_total},
            {"s1": s1, "s2": s2, "s3": s3},
            remark, has_vat
        )
        
        st.success("สร้าง PDF สำเร็จ!")
        st.download_button("📥 คลิกเพื่อดาวน์โหลด PDF", res_pdf, f"{doc_no}.pdf", "application/pdf", use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: จัดการฐานข้อมูลลูกค้า (Real-time Save + Rerun)
# ------------------------------------------------------------------
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    
    edited_customers = st.data_editor(
        st.session_state.db_customers, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        column_config={"ลบ": st.column_config.CheckboxColumn("ลบ", default=False)},
        key="db_cust_editor_final"
    )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลง (ลูกค้า)", type="primary", use_container_width=True):
        save_data(edited_customers, CUST_FILE)
        st.session_state.db_customers = edited_customers
        st.toast("✅ บันทึกข้อมูลลูกค้าสำเร็จ!")
        # คำสั่งนี้จะรีเฟรชหน้าจอทั้งหมด ทำให้ Tab 1 เห็นข้อมูลใหม่ทันที
        st.rerun()

# ------------------------------------------------------------------
# TAB 3: จัดการฐานข้อมูลสินค้า (Real-time Save + Rerun)
# ------------------------------------------------------------------
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    
    edited_products = st.data_editor(
        st.session_state.db_products, 
        column_order=("ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"),
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        column_config={"ลบ": st.column_config.CheckboxColumn("ลบ", default=False)},
        key="db_prod_editor_final"
    )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลง (สินค้า)", type="primary", use_container_width=True):
        save_data(edited_products, PROD_FILE)
        st.session_state.db_products = edited_products
        st.toast("✅ บันทึกข้อมูลสินค้าสำเร็จ!")
        # คำสั่งนี้จะรีเฟรชหน้าจอทั้งหมด ทำให้ Tab 1 เห็นข้อมูลใหม่ทันที
        st.rerun()

# ------------------------------------------------------------------
# TAB 4: ประวัติใบเสนอราคา (Fix StreamlitAPIException using Callback)
# ------------------------------------------------------------------
with tab4:
    st.header("🗂️ ประวัติใบเสนอราคา")
    
    if not st.session_state.db_history.empty:
        history_view = st.session_state.db_history[['timestamp', 'doc_no', 'customer', 'total']].copy()
        history_view.columns = ["วัน-เวลาที่สร้าง", "เลขที่เอกสาร", "ชื่อลูกค้า", "ยอดรวม"]
        
        # Selectbox ต้องมี Key เพื่อให้ Callback เรียกใช้ได้
        sel_history = st.selectbox(
            "เลือกเอกสารเพื่อโหลดข้อมูลกลับมาแก้ไข", 
            history_view["เลขที่เอกสาร"].tolist(),
            key="history_selector_box" 
        )
        
        # ใช้ on_click เพื่อรันฟังก์ชัน restore_history_callback ก่อนที่หน้าจอจะ Render ใหม่
        # วิธีนี้จะแก้ปัญหา "st.session_state cannot be modified after widget instantiated"
        st.button(
            "🔄 โหลดข้อมูลเก่ามาแก้ไข (Tab 1)", 
            use_container_width=True, 
            on_click=restore_history_callback 
        )
           
        st.divider()
        st.dataframe(history_view, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีประวัติการสร้างใบเสนอราคา")
