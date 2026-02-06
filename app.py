import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF
import json

# ==============================================================================
# 1. การตั้งค่าหน้าจอและสถานะเริ่มต้น (CONFIG & SESSION STATE)
# ==============================================================================
st.set_page_config(
    page_title="SIWAKIT TRADING SYSTEM", 
    layout="wide", 
    page_icon="🏢"
)

# กำหนดชื่อไฟล์สำหรับเก็บข้อมูล
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"
HISTORY_FILE = "history_quotes.csv"

# --- ส่วนของการโหลดข้อมูลเก่ากลับมาแก้ไข (Reload Logic) ---
if "reload_command" in st.session_state:
    target_doc = st.session_state.reload_command
    
    if os.path.exists(HISTORY_FILE):
        try:
            df_hist = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
            row = df_hist[df_hist['doc_no'] == target_doc]
            
            if not row.empty:
                # แปลงข้อมูล JSON กลับเป็น Dictionary
                saved_data = json.loads(row.iloc[0]['data_json'])
                
                # 1. คืนค่าตารางรายการสินค้า
                st.session_state.grid_df = pd.DataFrame.from_dict(saved_data['grid_df'])
                
                # 2. คืนค่าตัวแปรต่างๆ ในหน้าจอ (Widget Mapping)
                keys_map = {
                    "doc_no_in": "doc_no",
                    "doc_date_in": "doc_date",
                    "due_date_in": "due_date",
                    "valid_days_in": "valid_days",
                    "credit_in": "credit",
                    "exp_date_in": "exp_date",
                    "c_name_in": "c_name",
                    "contact_in": "contact",
                    "c_addr_in": "c_addr", 
                    "c_tel_in": "c_tel",
                    "c_fax_in": "c_fax",
                    "remark_in": "remark", 
                    "has_vat_in": "has_vat",
                    "s1_in": "s1",
                    "s2_in": "s2",
                    "s3_in": "s3",
                    "my_comp_in": "my_comp",
                    "my_addr_in": "my_addr",
                    "my_tel_in": "my_tel", 
                    "my_fax_in": "my_fax",
                    "my_tax_in": "my_tax"
                }
                
                for key_ss, key_json in keys_map.items():
                    if key_json in saved_data:
                        st.session_state[key_ss] = saved_data[key_json]
                
                st.toast(f"✅ โหลดข้อมูล {target_doc} เรียบร้อยแล้ว!", icon="🔄")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
            
    # ล้างสถานะการโหลดเพื่อไม่ให้รันซ้ำซ้อน
    del st.session_state.reload_command

# สร้างตารางเปล่าเริ่มต้นถ้ายังไม่มีข้อมูลใน Session
if "grid_df" not in st.session_state:
    st.session_state.grid_df = pd.DataFrame(
        [
            {"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}
            for _ in range(20)
        ]
    )

# ==============================================================================
# 2. ฟังก์ชันหลักสำหรับการจัดการข้อมูล (CORE FUNCTIONS)
# ==============================================================================

def load_databases():
    """โหลดข้อมูลจากไฟล์ CSV เข้าสู่ตัวแปรระบบ"""
    
    # --- โหลดฐานข้อมูลลูกค้า ---
    if "db_customers" not in st.session_state:
        if os.path.exists(CUST_FILE):
            try:
                df = pd.read_csv(CUST_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in df.columns:
                    df = df.drop(columns=['Unnamed: 0'])
                st.session_state.db_customers = df
            except:
                st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        
        if 'ลบ' not in st.session_state.db_customers.columns:
            st.session_state.db_customers.insert(0, 'ลบ', False)

    # --- โหลดฐานข้อมูลสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                df_p = pd.read_csv(PROD_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in df_p.columns:
                    df_p = df_p.drop(columns=['Unnamed: 0'])
                if 'รหัสสินค้า' in df_p.columns:
                    df_p['รหัสสินค้า'] = df_p['รหัสสินค้า'].astype(str)
                st.session_state.db_products = df_p
            except:
                st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
            
        if 'ลบ' not in st.session_state.db_products.columns:
            st.session_state.db_products.insert(0, 'ลบ', False)

    # --- โหลดประวัติใบเสนอราคา ---
    if "db_history" not in st.session_state:
        if os.path.exists(HISTORY_FILE):
            try:
                st.session_state.db_history = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
            except:
                st.session_state.db_history = pd.DataFrame(columns=["timestamp", "doc_no", "customer", "total", "data_json"])
        else:
            st.session_state.db_history = pd.DataFrame(columns=["timestamp", "doc_no", "customer", "total", "data_json"])

def save_csv(df, filename):
    """ฟังก์ชันบันทึก DataFrame ลงไฟล์ CSV"""
    temp = df.copy()
    if 'ลบ' in temp.columns:
        temp = temp.drop(columns=['ลบ'])
    if 'Unnamed: 0' in temp.columns:
        temp = temp.drop(columns=['Unnamed: 0'])
    temp.to_csv(filename, index=False, encoding='utf-8-sig')

def to_num(val):
    """แปลงค่าให้เป็นตัวเลขที่ปลอดภัย"""
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val) if val else 0.0
    except:
        return 0.0

# สั่งโหลดฐานข้อมูลทันทีเมื่อแอปทำงาน
load_databases()

# ==============================================================================
# 3. ฟังก์ชันสร้างไฟล์ PDF (PDF GENERATOR)
# ==============================================================================

def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # จัดการเรื่องฟอนต์ภาษาไทย
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path, uni=True)
        pdf.add_font('THSarabun', 'B', font_path, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial' 
    
    # ใส่ Logo (ถ้ามี)
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break

    # --- ส่วนหัว: ข้อมูลบริษัทเรา ---
    pdf.set_xy(35, 10)
    pdf.set_font(use_f, 'B', 14)
    header_text = (
        f"บริษัท: {d['my_comp']}\n"
        f"ที่อยู่: {d['my_addr']}\n"
        f"โทร: {d['my_tel']} โทรสาร: {d['my_fax']}\n"
        f"เลขผู้เสียภาษี: {d['my_tax']}"
    )
    pdf.multi_cell(100, 6, header_text, 0, 'L')

    # --- เลขที่และวันที่เอกสาร ---
    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0) # กรอบ
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    # หัวข้อใหญ่
    pdf.set_y(42)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # --- ส่วนข้อมูลลูกค้าและเงื่อนไข ---
    pdf.set_font(use_f, '', 14)
    pdf.ln(2)
    start_info_y = pdf.get_y()
    
    # ฝั่งซ้าย: ข้อมูลลูกค้า
    pdf.set_xy(10, start_info_y)
    cust_info = (
        f"ชื่อผู้ติดต่อ: {d['contact']}\n"
        f"บริษัท: {d['c_name']}\n"
        f"ที่อยู่: {d['c_addr']}\n"
        f"โทร: {d['c_tel']}  โทรสาร: {d['c_fax']}"
    )
    pdf.multi_cell(115, 6, cust_info, 0, 'L')
    y_left = pdf.get_y()
    
    # ฝั่งขวา: เงื่อนไขการขาย
    pdf.set_xy(130, start_info_y)
    terms_info = (
        f"วันที่กำหนดส่ง: {d['due_date']}\n"
        f"ยืนราคา (วัน): {d['valid_days']}  Expire Date: {d['exp_date']}\n"
        f"เครดิต (วัน): {d['credit']}"
    )
    pdf.multi_cell(75, 6, terms_info, 0, 'L')
    y_right = pdf.get_y()
    
    # ปรับตำแหน่ง Y ให้พ้นจากข้อมูลส่วนบน
    pdf.set_y(max(y_left, y_right) + 5)

    # --- ตารางรายการสินค้า ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 11)
    
    # กำหนดความกว้างคอลัมน์
    w = [15, 75, 15, 15, 25, 15, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 11)
    row_height = 6.0
    
    # วนลูปพิมพ์รายการสินค้า (Fix ที่ 20 บรรทัดเพื่อให้ฟอร์มดูเต็ม)
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

    # --- สรุปยอดเงิน ---
    pdf.ln(2)
    footer_y = pdf.get_y()
    
    # หมายเหตุด้านซ้าย
    pdf.set_xy(10, footer_y)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12)
    pdf.set_x(10)
    pdf.multi_cell(105, 5, remark_text, 0, 'L')
    
    # ตารางรวมเงินด้านขวา
    curr_y = footer_y
    label_x, val_x = 125, 175

    def add_total_row(label, value, is_bold=False, is_red=False):
        nonlocal curr_y
        pdf.set_font(use_f, 'B' if is_bold else '', 13 if is_bold else 12)
        if is_red:
            pdf.set_text_color(180, 0, 0)
        else:
            pdf.set_text_color(0, 0, 0)
            
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

    # --- ส่วนเซ็นชื่อ (ท้ายกระดาษ) ---
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

# ==============================================================================
# 4. ส่วนแสดงผล UI (TABS)
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 สร้างใบเสนอราคา", 
    "👥 ฐานข้อมูลลูกค้า", 
    "📦 ฐานข้อมูลสินค้า", 
    "🗂️ ประวัติใบเสนอราคา"
])

# ------------------------------------------------------------------------------
# TAB 1: การสร้างเอกสาร (Quotation)
# ------------------------------------------------------------------------------
with tab1:
    col_comp_info, col_doc_info = st.columns(2)
    
    with col_comp_info:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัท", "บริษัท ศิวกิจ เทรดดิ้ง จำกัด", key="my_comp_in")
        my_addr = st.text_input("ที่อยู่บริษัท", "", key="my_addr_in") 
        my_tel = st.text_input("โทรศัพท์", "", key="my_tel_in")      
        my_fax = st.text_input("โทรสาร", "", key="my_fax_in")        
        my_tax = st.text_input("เลขผู้เสียภาษี", "", key="my_tax_in")
    
    with col_doc_info:
        st.subheader("📄 รายละเอียดเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d')}-001", key="doc_no_in")
        
        # --- [SYSTEM LOGIC] ตรวจสอบเลขที่ซ้ำในระบบ ---
        is_duplicate = False
        if not st.session_state.db_history.empty:
            if doc_no in st.session_state.db_history['doc_no'].values:
                is_duplicate = True
                st.error(f"⚠️ เลขที่เอกสาร '{doc_no}' นี้มีอยู่ในระบบแล้ว! โปรดเปลี่ยนเลขเพื่อป้องกันการบันทึกซ้ำ")
        
        doc_date = st.text_input("วันที่ออกเอกสาร", datetime.now().strftime('%d/%m/%Y'), key="doc_date_in")
        due_date = st.text_input("วันที่กำหนดส่ง", "7 วัน", key="due_date_in")
        
        v_col_1, v_col_2 = st.columns(2)
        valid_days = v_col_1.text_input("ยืนราคา (วัน)", "30", key="valid_days_in")
        exp_date = v_col_2.text_input("Expire Date", datetime.now().strftime('%d/%m/%Y'), key="exp_date_in")
        credit = st.text_input("เครดิต (วัน)", "30", key="credit_in")

    st.divider()

    # --- ฟังก์ชันช่วยดึงข้อมูลลูกค้าจาก DB ---
    def update_customer_fields():
        selected_name = st.session_state.cust_selector
        if selected_name and selected_name != "-- กรอกใหม่ / พิมพ์เอง --":
            found = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == selected_name]
            if not found.empty:
                r = found.iloc[0]
                st.session_state.c_name_in = str(r.get('ชื่อบริษัท', ''))
                st.session_state.contact_in = str(r.get('ผู้ติดต่อ', ''))
                st.session_state.c_addr_in = str(r.get('ที่อยู่', ''))
                st.session_state.c_tel_in = str(r.get('โทร', ''))
                st.session_state.c_fax_in = str(r.get('แฟกซ์', ''))

    st.subheader("👤 ข้อมูลลูกค้า")
    current_customers = st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist()
    c_list_options = ["-- กรอกใหม่ / พิมพ์เอง --"] + [str(x) for x in current_customers if str(x).strip() != ""]
    
    st.selectbox("📥 ดึงข้อมูลจากฐานข้อมูลเก่า", c_list_options, key="cust_selector", on_change=update_customer_fields)

    col_c_1, col_c_2 = st.columns(2)
    with col_c_1:
        c_name = st.text_input("ชื่อบริษัทลูกค้า", key="c_name_in")
        contact = st.text_input("ชื่อผู้ติดต่อ", key="contact_in")
        c_addr = st.text_area("ที่อยู่จัดส่ง/วางบิล", height=70, key="c_addr_in")
    with col_c_2:
        st.write("<br><br>", unsafe_allow_html=True) 
        c_tel = st.text_input("เบอร์โทรศัพท์ลูกค้า", key="c_tel_in")
        c_fax = st.text_input("เบอร์แฟกซ์ลูกค้า", key="c_fax_in")

    # --- ตารางรายการสินค้า (Data Editor) ---
    st.subheader("📦 รายการสินค้า")
    current_products_list = st.session_state.db_products['รหัสสินค้า'].dropna().unique().tolist()
    p_codes_options = [str(x) for x in current_products_list if str(x).strip() != ""]
    
    edited_df = st.data_editor(
        st.session_state.grid_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัสสินค้า", options=p_codes_options, width="medium"),
            "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
            "จำนวน": st.column_config.NumberColumn("จำนวน", min_value=0, format="%.2f"),
            "ราคา": st.column_config.NumberColumn("ราคา/หน่วย", min_value=0, format="%.2f"),
            "ส่วนลด": st.column_config.NumberColumn("ส่วนลด", format="%.2f")
        },
        column_order=("รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา", "ส่วนลด"),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_main_grid"
    )

    # --- ระบบ Auto-Fill ข้อมูลสินค้าเมื่อเลือกรหัสสินค้า ---
    needs_refresh_editor = False
    for idx, row in edited_df.iterrows():
        item_code = str(row['รหัสสินค้า'])
        if item_code and item_code in p_codes_options:
            found_prod_df = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'].astype(str) == item_code]
            if not found_prod_df.empty:
                prod_data = found_prod_df.iloc[0]
                # ถ้าในตารางยังไม่มีชื่อรายการ ให้ดึงมาใส่
                if row['รายการ'] != prod_data['รายการ'] and (row['รายการ'] == "" or row['รายการ'] is None):
                    edited_df.at[idx, 'รายการ'] = prod_data['รายการ']
                    edited_df.at[idx, 'หน่วย'] = prod_data['หน่วย']
                    edited_df.at[idx, 'ราคา'] = prod_data['ราคา']
                    needs_refresh_editor = True

    if needs_refresh_editor:
        st.session_state.grid_df = edited_df
        st.rerun()
    else:
        st.session_state.grid_df = edited_df

    # --- การคำนวณยอดเงิน ---
    calc_df = edited_df.copy()
    calc_df['qty_num'] = calc_df['จำนวน'].apply(to_num)
    calc_df['price_num'] = calc_df['ราคา'].apply(to_num)
    calc_df['disc_num'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['รวมเงิน'] = (calc_df['qty_num'] * calc_df['price_num']) - calc_df['disc_num']
    
    sum_gross_val = (calc_df['qty_num'] * calc_df['price_num']).sum()
    sum_discount_val = calc_df['disc_num'].sum()
    sum_subtotal_val = calc_df['รวมเงิน'].sum()

    col_foot_left, col_foot_right = st.columns([2, 1])
    
    with col_foot_left:
        remark_text_area = st.text_area(
            "📝 หมายเหตุ", 
            value="1. สินค้ารับประกัน 1 ปี\n2. กำหนดยืนราคาตามที่ระบุในเอกสาร", 
            key="remark_in"
        )
        
    with col_foot_right:
        st.write("### สรุปยอดเงิน")
        has_vat_check = st.checkbox("คิด VAT 7%", value=True, key="has_vat_in")
        vat_amount = (sum_subtotal_val * 0.07) if has_vat_check else 0.0
        grand_total_val = sum_subtotal_val + vat_amount

        st.write(f"รวมเป็นเงิน: {sum_gross_val:,.2f}")
        st.write(f"ส่วนลดทั้งหมด: -{sum_discount_val:,.2f}")
        st.write(f"ยอดหลังหักส่วนลด: {sum_subtotal_val:,.2f}")
        if has_vat_check:
            st.write(f"ภาษีมูลค่าเพิ่ม 7%: {vat_amount:,.2f}")
        st.metric("ยอดรวมทั้งสิ้น", f"{grand_total_val:,.2f} บาท")

    # ส่วนของพนักงานและลูกค้า
    col_sig_1, col_sig_2, col_sig_3 = st.columns(3)
    sig_1 = col_sig_1.text_input("ชื่อลูกค้า (ผู้อนุมัติ)", key="s1_in")
    sig_2 = col_sig_2.text_input("ชื่อพนักงานขาย", key="s2_in")
    sig_3 = col_sig_3.text_input("ชื่อผู้จัดการ", key="s3_in")

    # --- ปุ่มดำเนินการหลัก ---
    if st.button("🚀 สร้าง PDF และบันทึกประวัติ", type="primary", use_container_width=True):
        if not c_name:
            st.error("⚠️ ไม่สามารถดำเนินการได้: กรุณาระบุชื่อบริษัทลูกค้า")
        elif is_duplicate:
            st.error("❌ บันทึกไม่ได้: เลขที่เอกสารซ้ำ! โปรดเปลี่ยนเลขที่ใบเสนอราคาในหัวข้อ 'รายละเอียดเอกสาร'")
        else:
            # เก็บข้อมูลลงประวัติ (History)
            history_record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "doc_no": doc_no,
                "customer": c_name,
                "total": grand_total_val,
                "data_json": json.dumps({
                    "grid_df": edited_df.to_dict(),
                    "doc_date": doc_date, "due_date": due_date, "valid_days": valid_days, 
                    "credit": credit, "exp_date": exp_date,
                    "c_name": c_name, "contact": contact, "c_addr": c_addr, 
                    "c_tel": c_tel, "c_fax": c_fax,
                    "remark": remark_text_area, "has_vat": has_vat_check, 
                    "s1": sig_1, "s2": sig_2, "s3": sig_3,
                    "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, 
                    "my_fax": my_fax, "my_tax": my_tax
                }, ensure_ascii=False)
            }
            
            # รวมประวัติใหม่เข้าไป
            new_hist_df = pd.DataFrame([history_record])
            st.session_state.db_history = pd.concat([new_hist_df, st.session_state.db_history], ignore_index=True)
            save_csv(st.session_state.db_history, HISTORY_FILE)
            st.toast("บันทึกประวัติสำเร็จ!", icon="💾")

            # สร้างข้อมูลสำหรับ PDF
            pdf_data_dict = {
                "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
                "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "valid_days": valid_days,
                "exp_date": exp_date, "credit": credit, "c_name": c_name, "contact": contact,
                "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax
            }
            
            pdf_summary = {
                "gross": sum_gross_val, "discount": sum_discount_val, 
                "subtotal": sum_subtotal_val, "vat": vat_amount, 
                "grand_total": grand_total_val
            }
            
            pdf_signatures = {"s1": sig_1, "s2": sig_2, "s3": sig_3}
            
            # เรียกฟังก์ชันสร้างไฟล์ PDF
            result_pdf_bytes = create_pdf(
                pdf_data_dict, calc_df, pdf_summary, pdf_signatures, 
                remark_text_area, has_vat_check
            )
            
            st.success("สร้างเอกสารสำเร็จ!")
            st.download_button(
                label="📥 ดาวน์โหลดใบเสนอราคา (PDF)",
                data=result_pdf_bytes,
                file_name=f"{doc_no}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    if st.button("🔄 ล้างหน้าจอเพื่อเริ่มใบใหม่", use_container_width=True):
        st.session_state.grid_df = pd.DataFrame(
            [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0} for _ in range(20)]
        )
        keys_to_clear = [
            "doc_no_in", "c_name_in", "contact_in", "c_addr_in", 
            "c_tel_in", "c_fax_in", "cust_selector"
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

# ------------------------------------------------------------------------------
# TAB 2: จัดการลูกค้า (Customer Database)
# ------------------------------------------------------------------------------
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    st.info("แก้ไขข้อมูลในตารางแล้วกด 'บันทึกลูกค้า' | หากต้องการลบให้ติ๊กช่อง 'ลบ?' แล้วกดปุ่มลบ")
    
    edited_cust_db = st.data_editor(
        st.session_state.db_customers, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        column_config={"ลบ": st.column_config.CheckboxColumn("ลบ?", default=False, width="small")},
        key="customer_table_editor"
    )
    
    col_c_btn1, col_c_btn2 = st.columns(2)
    with col_c_btn1:
        if st.button("💾 บันทึกการเปลี่ยนแปลงข้อมูลลูกค้า", type="primary", use_container_width=True):
            st.session_state.db_customers = edited_cust_db
            save_csv(edited_cust_db, CUST_FILE)
            st.toast("✅ ข้อมูลลูกค้าได้รับการอัปเดตแล้ว")
            st.rerun()
            
    with col_c_btn2:
        if st.button("❌ ลบรายชื่อลูกค้าที่เลือก", use_container_width=True):
            remaining_cust = edited_cust_db[edited_cust_db['ลบ'] == False]
            st.session_state.db_customers = remaining_cust
            save_csv(remaining_cust, CUST_FILE)
            st.toast("🗑️ ลบข้อมูลเรียบร้อย")
            st.rerun()

# ------------------------------------------------------------------------------
# TAB 3: จัดการสินค้า (Product Database)
# ------------------------------------------------------------------------------
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    st.info("คุณสามารถเพิ่มรายการสินค้าใหม่ได้ที่แถวล่างสุดของตาราง")
    
    edited_prod_db = st.data_editor(
        st.session_state.db_products, 
        column_order=("ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"),
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        column_config={"ลบ": st.column_config.CheckboxColumn("ลบ?", default=False, width="small")},
        key="product_table_editor"
    )
    
    col_p_btn1, col_p_btn2 = st.columns(2)
    with col_p_btn1:
        if st.button("💾 บันทึกการเปลี่ยนแปลงสินค้า", type="primary", use_container_width=True):
            st.session_state.db_products = edited_prod_db
            save_csv(edited_prod_db, PROD_FILE)
            st.toast("✅ ข้อมูลสินค้าได้รับการอัปเดตแล้ว")
            st.rerun()
            
    with col_p_btn2:
        if st.button("❌ ลบรายการสินค้าที่เลือก", use_container_width=True):
            remaining_prod = edited_prod_db[edited_prod_db['ลบ'] == False]
            st.session_state.db_products = remaining_prod
            save_csv(remaining_prod, PROD_FILE)
            st.toast("🗑️ ลบข้อมูลเรียบร้อย")
            st.rerun()

# ------------------------------------------------------------------------------
# TAB 4: ประวัติ (History Management)
# ------------------------------------------------------------------------------
with tab4:
    st.header("🗂️ ประวัติใบเสนอราคา")
    
    if not st.session_state.db_history.empty:
        # ส่วนสำหรับการเรียกข้อมูลเก่ามาแก้ไข
        all_doc_numbers = st.session_state.db_history["doc_no"].tolist()
        selected_to_reload = st.selectbox(
            "เลือกเลขที่เอกสารที่ต้องการดึงมาแก้ไข:", 
            all_doc_numbers, 
            key="history_reloader"
        )
        
        if st.button("🔄 โหลดข้อมูลนี้กลับไปแก้ไข (จะไปที่ Tab 1)", use_container_width=True, type="primary"):
            st.session_state.reload_command = selected_to_reload
            st.rerun()
            
        st.divider()
        st.subheader("รายการประวัติทั้งหมด")
        
        # ตารางแสดงประวัติเพื่อดูหรือลบ
        edited_history_db = st.data_editor(
            st.session_state.db_history,
            column_config={
                "ลบ": st.column_config.CheckboxColumn("ลบประวัติ", default=False),
                "timestamp": st.column_config.TextColumn("วัน-เวลา", disabled=True),
                "doc_no": st.column_config.TextColumn("เลขที่", disabled=True),
                "customer": st.column_config.TextColumn("ลูกค้า", disabled=True),
                "total": st.column_config.NumberColumn("ยอดรวม", format="%.2f", disabled=True),
                "data_json": None # ซ่อนข้อมูลดิบ JSON
            },
            column_order=("ลบ", "timestamp", "doc_no", "customer", "total"),
            use_container_width=True,
            hide_index=True,
            key="history_main_table"
        )
        
        if st.button("🗑️ ยืนยันการลบประวัติที่เลือก", use_container_width=True):
            remaining_history = edited_history_db[edited_history_db['ลบ'] == False]
            st.session_state.db_history = remaining_history
            save_csv(remaining_history, HISTORY_FILE)
            st.toast("🗑️ ลบประวัติเรียบร้อยแล้ว")
            st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลประวัติในระบบ")
