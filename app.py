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
                temp_df = temp_df.reset_index(drop=True)
                st.session_state.db_customers = temp_df
            except:
                st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            st.session_state.db_customers = pd.DataFrame([
                {"ลบ": False, "รหัส": "C001", "ชื่อบริษัท": "บริษัท ตัวอย่าง จำกัด", "ผู้ติดต่อ": "คุณสมชาย", "ที่อยู่": "123 กทม.", "โทร": "081-111-1111", "แฟกซ์": "02-222-2222"}
            ])
        
        # ตรวจสอบและสร้างคอลัมน์ ลบ
        if 'ลบ' not in st.session_state.db_customers.columns:
            st.session_state.db_customers.insert(0, 'ลบ', False)
        st.session_state.db_customers['ลบ'] = st.session_state.db_customers['ลบ'].fillna(False).astype(bool)

    # --- 2. โหลดข้อมูลสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                temp_df_p = pd.read_csv(PROD_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df_p.columns: 
                    temp_df_p = temp_df_p.drop(columns=['Unnamed: 0'])
                if 'รหัสสินค้า' in temp_df_p.columns:
                    temp_df_p['รหัสสินค้า'] = temp_df_p['รหัสสินค้า'].astype(str)
                temp_df_p = temp_df_p.reset_index(drop=True)
                st.session_state.db_products = temp_df_p
            except:
                st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            st.session_state.db_products = pd.DataFrame([
                {"ลบ": False, "รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง A", "ราคา": 1500.0, "หน่วย": "ชิ้น"}
            ])
        
        if 'ลบ' not in st.session_state.db_products.columns:
            st.session_state.db_products.insert(0, 'ลบ', False)
        st.session_state.db_products['ลบ'] = st.session_state.db_products['ลบ'].fillna(False).astype(bool)

    # --- 3. โหลดประวัติใบเสนอราคา ---
    if "db_history" not in st.session_state:
        if os.path.exists(HISTORY_FILE):
            try:
                temp_hist = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
                # เพิ่มคอลัมน์ "ลบ" สำหรับหน้าประวัติ
                if 'ลบ' not in temp_hist.columns:
                    temp_hist.insert(0, 'ลบ', False)
                temp_hist['ลบ'] = temp_hist['ลบ'].fillna(False).astype(bool)
                st.session_state.db_history = temp_hist
            except:
                 st.session_state.db_history = pd.DataFrame(columns=["ลบ", "timestamp", "doc_no", "customer", "total", "data_json"])
        else:
            st.session_state.db_history = pd.DataFrame(columns=["ลบ", "timestamp", "doc_no", "customer", "total", "data_json"])

def save_data(df, filename):
    """ฟังก์ชันบันทึก Dataframe ลง CSV"""
    df_to_save = df.copy()
    
    # แปลงคอลัมน์ลบเป็น bool เสมอ
    if 'ลบ' in df_to_save.columns:
        df_to_save['ลบ'] = df_to_save['ลบ'].fillna(False).astype(bool)

    # กรองแถวว่าง (กรณีไม่ใช่ History)
    if 'รหัสสินค้า' in df_to_save.columns:
        df_to_save = df_to_save[df_to_save['รหัสสินค้า'].astype(str).str.strip() != ""]
    elif 'ชื่อบริษัท' in df_to_save.columns:
        df_to_save = df_to_save[df_to_save['ชื่อบริษัท'].astype(str).str.strip() != ""]

    if 'Unnamed: 0' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['Unnamed: 0'])
    
    df_to_save = df_to_save.reset_index(drop=True)
    df_to_save.to_csv(filename, index=False, encoding='utf-8-sig')
    return df_to_save

def to_num(val):
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val) if val else 0.0
    except:
        return 0.0

# เรียกใช้โหลดข้อมูล
load_data()

# ==========================================
# 3. PDF ENGINE
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path, uni=True)
        pdf.add_font('THSarabun', 'B', font_path, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
            
    pdf.set_xy(35, 10)
    pdf.set_font(use_f, 'B', 14)
    header_text = f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}"
    pdf.multi_cell(100, 6, header_text, 0, 'L')

    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0)
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    pdf.set_y(42)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

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
    
    pdf.set_xy(10, footer_y)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12)
    pdf.set_x(10)
    pdf.multi_cell(105, 5, remark_text, 0, 'L')
    
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
# 4. CALLBACK FUNCTIONS
# ==========================================
def update_customer_fields():
    """Callback function เพื่ออัปเดตข้อมูลลูกค้าทันทีเมื่อเลือก Dropdown"""
    selected_val = st.session_state.cust_selector_tab1
    if selected_val and selected_val != "-- พิมพ์เอง --":
        # ค้นหาข้อมูลจาก DataFrame
        found = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == selected_val]
        if not found.empty:
            row = found.iloc[0]
            # อัปเดต Session State ของ Text Input โดยตรง
            st.session_state.c_name_in = str(row['ชื่อบริษัท'])
            st.session_state.contact_in = str(row['ผู้ติดต่อ']) if pd.notna(row['ผู้ติดต่อ']) else ""
            st.session_state.c_addr_in = str(row['ที่อยู่']) if pd.notna(row['ที่อยู่']) else ""
            st.session_state.c_tel_in = str(row['โทร']) if pd.notna(row['โทร']) else ""
            st.session_state.c_fax_in = str(row['แฟกซ์']) if pd.notna(row['แฟกซ์']) else ""

def restore_history_callback():
    sel_doc = st.session_state.get("history_selector_box")
    if sel_doc:
        row_data = st.session_state.db_history[st.session_state.db_history['doc_no'] == sel_doc].iloc[0]
        saved_data = json.loads(row_data['data_json'])
        
        st.session_state.grid_df = pd.DataFrame.from_dict(saved_data['grid_df'])
        
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

def clear_all_data():
    """ฟังก์ชันเคลียร์ข้อมูลจริง โดยการเคลียร์ Session State keys"""
    # 1. รีเซ็ตตาราง
    st.session_state.grid_df = pd.DataFrame(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 20
    )
    # 2. รีเซ็ตค่าใน Input Fields ทั้งหมดผ่าน Session State Key
    keys_to_reset = [
        "c_name_in", "contact_in", "c_addr_in", "c_tel_in", "c_fax_in",
        "remark_in", "s1_in", "s2_in", "s3_in"
    ]
    for k in keys_to_reset:
        st.session_state[k] = ""
    
    # รีเซ็ต Dropdown
    st.session_state["cust_selector_tab1"] = "-- พิมพ์เอง --"
    # รีเซ็ตเลขที่เอกสารเป็นตัวใหม่
    st.session_state["doc_no_in"] = f"QT-{datetime.now().strftime('%Y%m%d')}-001"
    
    st.toast("ข้อมูลถูกล้างเรียบร้อยแล้ว", icon="🗑️")

# ==========================================
# 5. USER INTERFACE
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า", "🗂️ ประวัติใบเสนอราคา"])

# ------------------------------------------------------------------
# TAB 1: Quotation
# ------------------------------------------------------------------
with tab1:
    h_col1, h_col2 = st.columns([0.85, 0.15])
    with h_col1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
    with h_col2:
        # ใช้ on_click เพื่อเรียกฟังก์ชัน clear_all_data โดยตรงก่อน render
        st.button("🧹 เคลียร์ข้อมูล", on_click=clear_all_data, type="secondary", use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        my_comp = st.text_input("ชื่อบริษัท", "บริษัท ศิวกิจ เทรดดิ้ง จำกัด", key="my_comp_in")
        my_addr = st.text_input("ที่อยู่บริษัท", "", key="my_addr_in") 
        my_tel = st.text_input("โทรศัพท์", "", key="my_tel_in")      
        my_fax = st.text_input("โทรสาร", "", key="my_fax_in")        
        my_tax = st.text_input("เลขผู้เสียภาษี", "", key="my_tax_in")
    
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

    c_h1, c_h2 = st.columns([1, 1])
    with c_h1: st.subheader("👤 ข้อมูลลูกค้า")
    with c_h2: 
        current_customers = st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist()
        c_list = ["-- พิมพ์เอง --"] + [str(x) for x in current_customers if str(x).strip() != ""]
        
        sel_c = st.selectbox(
            "📥 ดึงข้อมูลลูกค้าเก่า", 
            c_list, 
            key="cust_selector_tab1",
            on_change=update_customer_fields 
        )

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        c_name = st.text_input("ชื่อบริษัทลูกค้า", key="c_name_in")
        contact = st.text_input("ชื่อผู้ติดต่อ", key="contact_in")
        c_addr = st.text_area("ที่อยู่จัดส่ง/วางบิล", height=70, key="c_addr_in")
    with c_col2:
        st.write("<br><br>", unsafe_allow_html=True) 
        c_tel = st.text_input("เบอร์โทรศัพท์ลูกค้า", key="c_tel_in")
        c_fax = st.text_input("เบอร์แฟกซ์ลูกค้า", key="c_fax_in")

    st.subheader("📦 รายการสินค้า")
    current_products = st.session_state.db_products['รหัสสินค้า'].dropna().unique().tolist()
    p_codes = [str(x) for x in current_products if str(x).strip() != ""]
    current_df = st.session_state.grid_df.fillna(0)
    
    # เพิ่ม num_rows="dynamic" และ key="editor_main" เพื่อจับ Event
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

    # Logic การค้นหาสินค้าอัตโนมัติเมื่อเลือก Code
    needs_rerun = False
    for idx, row in edited_df.iterrows():
        code = str(row['รหัสสินค้า'])
        if code and code in p_codes:
            found_prod = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'].astype(str) == code]
            if not found_prod.empty:
                p_info = found_prod.iloc[0]
                # ถ้าชื่อรายการยังว่าง หรือ ไม่ตรงกับฐานข้อมูล (กรณีเพิ่งเลือก) ให้เติมข้อมูล
                if row['รายการ'] != p_info['รายการ']:
                    edited_df.at[idx, 'รายการ'] = p_info['รายการ']
                    edited_df.at[idx, 'หน่วย'] = p_info['หน่วย']
                    edited_df.at[idx, 'ราคา'] = p_info['ราคา']
                    needs_rerun = True

    # อัปเดตข้อมูลกลับเข้า Session State เพื่อให้หน้าจจำค่าล่าสุด
    st.session_state.grid_df = edited_df

    if needs_rerun:
        st.rerun()

    # --- ส่วนคำนวณเงิน Real Time ---
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
        # Checkbox VAT: เมื่อติ๊กจะ Rerun และคำนวณใหม่ทันที
        has_vat = st.checkbox("คิด VAT 7%", value=True, key="has_vat_in")
        
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
        # --- ตรวจสอบเลขที่เอกสารซ้ำ ---
        is_duplicate = False
        if not st.session_state.db_history.empty:
             if doc_no in st.session_state.db_history['doc_no'].values:
                 is_duplicate = True
        
        if is_duplicate:
            st.error(f"⚠️ บันทึกไม่สำเร็จ: เลขที่ '{doc_no}' มีอยู่แล้วในประวัติ กรุณาเปลี่ยนเลขที่ใหม่")
        else:
            history_data = {
                "ลบ": False,
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
# TAB 2: ลูกค้า (REVERTED TO ORIGINAL LOGIC)
# ------------------------------------------------------------------
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    
    edited_customers = st.data_editor(
        st.session_state.db_customers, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True, 
        column_config={"ลบ": st.column_config.CheckboxColumn("ลบ?", default=False, width="small")},
        key="db_cust_editor_final"
    )
    
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        if st.button("💾 บันทึกการแก้ไข/เพิ่มใหม่", type="primary", use_container_width=True, key="btn_save_customer"):
            st.session_state.db_customers = edited_customers
            save_data(edited_customers, CUST_FILE)
            st.toast("✅ บันทึกข้อมูลเรียบร้อย")
            st.rerun()

    with col_c2:
        if st.button("❌ ลบรายการที่ติ๊กถูก (Check)", use_container_width=True, key="btn_del_customer"):
            df_to_keep = edited_customers[edited_customers['ลบ'] == False]
            st.session_state.db_customers = df_to_keep
            save_data(df_to_keep, CUST_FILE)
            st.toast("🗑️ ลบรายการเรียบร้อย")
            st.rerun()

# ------------------------------------------------------------------
# TAB 3: สินค้า (REVERTED TO ORIGINAL LOGIC)
# ------------------------------------------------------------------
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    
    edited_products = st.data_editor(
        st.session_state.db_products, 
        column_order=("ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"),
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True, 
        column_config={"ลบ": st.column_config.CheckboxColumn("ลบ?", default=False, width="small")},
        key="db_prod_editor_final"
    )
    
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        if st.button("💾 บันทึกการแก้ไข/เพิ่มใหม่", type="primary", use_container_width=True, key="btn_save_product"):
            st.session_state.db_products = edited_products
            save_data(edited_products, PROD_FILE)
            st.toast("✅ บันทึกข้อมูลเรียบร้อย")
            st.rerun()

    with col_p2:
        if st.button("❌ ลบรายการที่ติ๊กถูก (Check)", use_container_width=True, key="btn_del_product"):
            df_p_keep = edited_products[edited_products['ลบ'] == False]
            st.session_state.db_products = df_p_keep
            save_data(df_p_keep, PROD_FILE)
            st.toast("🗑️ ลบรายการเรียบร้อย")
            st.rerun()

# ------------------------------------------------------------------
# TAB 4: ประวัติ
# ------------------------------------------------------------------
with tab4:
    st.header("🗂️ ประวัติใบเสนอราคา")
    
    if not st.session_state.db_history.empty:
        # ส่วนสำหรับการเลือกและโหลดข้อมูล
        sel_history = st.selectbox(
            "เลือกเอกสารเพื่อโหลดข้อมูลกลับมาแก้ไข", 
            st.session_state.db_history["doc_no"].tolist(),
            key="history_selector_box" 
        )
        
        st.button(
            "🔄 โหลดข้อมูลเก่ามาแก้ไข (Tab 1)", 
            use_container_width=True, 
            on_click=restore_history_callback 
        )
            
        st.divider()
        
        # ส่วนแสดงตารางพร้อมความสามารถในการลบ
        st.subheader("รายการประวัติทั้งหมด")
        
        edited_history = st.data_editor(
            st.session_state.db_history,
            column_config={
                "ลบ": st.column_config.CheckboxColumn("ลบประวัติ", default=False),
                "timestamp": st.column_config.TextColumn("วัน-เวลาที่สร้าง", disabled=True),
                "doc_no": st.column_config.TextColumn("เลขที่เอกสาร", disabled=True),
                "customer": st.column_config.TextColumn("ชื่อลูกค้า", disabled=True),
                "total": st.column_config.NumberColumn("ยอดรวม", format="%.2f", disabled=True),
                "data_json": None  # ซ่อนคอลัมน์ JSON
            },
            column_order=("ลบ", "timestamp", "doc_no", "customer", "total"),
            use_container_width=True,
            hide_index=True,
            key="history_table_editor"
        )
        
        if st.button("🗑️ ยืนยันการลบประวัติที่เลือก", use_container_width=True, type="secondary"):
            df_hist_keep = edited_history[edited_history['ลบ'] == False]
            st.session_state.db_history = df_hist_keep
            save_data(df_hist_keep, HISTORY_FILE)
            st.toast("🗑️ ลบประวัติเรียบร้อยแล้ว")
            st.rerun()
            
    else:
        st.info("ยังไม่มีประวัติการสร้างใบเสนอราคา")
