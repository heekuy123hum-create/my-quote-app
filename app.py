import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import json
from fpdf import FPDF

# ==========================================
# 1. DATABASE SYSTEM & CONFIGURATION
# ==========================================
st.set_page_config(page_title="SIWAKIT TRADING SYSTEM", layout="wide", page_icon="🏢")

# --- CSS ตกแต่ง UI ---
st.markdown("""
<style>
    /* ปรับฟอนต์ให้ดูทันสมัย */
    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    /* ปรับแต่งปุ่มกด */
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    /* กล่องยอดเงินรวม */
    .metric-card {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 20px;
        border-radius: 10px;
        color: #155724;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 10px;
    }
    .metric-label {
        font-size: 1.2rem;
        margin-bottom: 5px;
        font-weight: bold;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #28a745;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    /* ซ่อน VAT ถ้าไม่ได้เลือก */
    .vat-hidden {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ชื่อไฟล์สำหรับเก็บข้อมูล
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"
HISTORY_FILE = "history_quotes.csv"
FONT_PATH = "THSarabunNew.ttf" 

# เริ่มต้นตัวแปร Session State
if "grid_df" not in st.session_state:
    # เริ่มต้น 15 บรรทัดเพื่อให้พอดีกับหน้า A4 ที่ฟอนต์ใหญ่ขึ้น
    st.session_state.grid_df = pd.DataFrame(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0.0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 15
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
                if 'Unnamed: 0' in temp_df.columns: temp_df = temp_df.drop(columns=['Unnamed: 0'])
                st.session_state.db_customers = temp_df
            except:
                st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            # ตัวอย่างข้อมูล
            st.session_state.db_customers = pd.DataFrame([
                {"ลบ": False, "รหัส": "C001", "ชื่อบริษัท": "ลูกค้าทั่วไป (เงินสด)", "ผู้ติดต่อ": "-", "ที่อยู่": "-", "โทร": "-", "แฟกซ์": "-"}
            ])
        
        if 'ลบ' not in st.session_state.db_customers.columns:
            st.session_state.db_customers.insert(0, 'ลบ', False)
        st.session_state.db_customers['ลบ'] = st.session_state.db_customers['ลบ'].fillna(False).astype(bool)

    # --- 2. โหลดข้อมูลสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                temp_df_p = pd.read_csv(PROD_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df_p.columns: temp_df_p = temp_df_p.drop(columns=['Unnamed: 0'])
                if 'รหัสสินค้า' in temp_df_p.columns:
                    temp_df_p['รหัสสินค้า'] = temp_df_p['รหัสสินค้า'].astype(str)
                st.session_state.db_products = temp_df_p
            except:
                st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            st.session_state.db_products = pd.DataFrame([
                {"ลบ": False, "รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง", "ราคา": 1000.0, "หน่วย": "ชิ้น"}
            ])
        
        if 'ลบ' not in st.session_state.db_products.columns:
            st.session_state.db_products.insert(0, 'ลบ', False)
        st.session_state.db_products['ลบ'] = st.session_state.db_products['ลบ'].fillna(False).astype(bool)

    # --- 3. โหลดประวัติ ---
    if "db_history" not in st.session_state:
        if os.path.exists(HISTORY_FILE):
            try:
                temp_hist = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
                if 'ลบ' not in temp_hist.columns: temp_hist.insert(0, 'ลบ', False)
                if 'Unnamed: 0' in temp_hist.columns: temp_hist = temp_hist.drop(columns=['Unnamed: 0'])
                st.session_state.db_history = temp_hist
            except:
                st.session_state.db_history = pd.DataFrame(columns=["ลบ", "timestamp", "doc_no", "customer", "total", "data_json"])
        else:
            st.session_state.db_history = pd.DataFrame(columns=["ลบ", "timestamp", "doc_no", "customer", "total", "data_json"])

def save_data(df, filename, key_col=None):
    """ฟังก์ชันบันทึก Dataframe ลง CSV แบบคลีนๆ"""
    df_to_save = df.copy()
    
    if 'ลบ' in df_to_save.columns:
        # กรองเอาเฉพาะที่ไม่ได้ติ๊กลบ
        df_to_save = df_to_save[df_to_save['ลบ'] == False]
        # แล้วเอาคอลัมน์ 'ลบ' ออกก่อนบันทึก
        df_to_save['ลบ'] = False

    # กรองแถวว่าง (ถ้ามี key_col)
    if key_col and key_col in df_to_save.columns:
         df_to_save = df_to_save[df_to_save[key_col].astype(str).str.strip() != ""]

    if 'Unnamed: 0' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['Unnamed: 0'])
    
    # Reset Index เพื่อไม่ให้มีเลข 0,1,2 ติดไป
    df_to_save = df_to_save.reset_index(drop=True)
    
    df_to_save.to_csv(filename, index=False, encoding='utf-8-sig')
    return df_to_save

def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val is not None else 0.0
    except:
        return 0.0

load_data()

# ==========================================
# 3. PDF ENGINE
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    # ตั้งค่าหน้ากระดาษ A4 (210mm x 297mm)
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(15, 15, 15) # ขอบซ้ายขวา 15mm
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # จัดการฟอนต์
    if os.path.exists(FONT_PATH):
        pdf.add_font('THSarabun', '', FONT_PATH, uni=True)
        pdf.add_font('THSarabun', 'B', FONT_PATH, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # --- ส่วนหัว (Header) ---
    # โลโก้
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=15, y=10, w=25)
            break
            
    # บริษัทเรา (เพิ่มขนาดตัวอักษร)
    pdf.set_xy(45, 10)
    pdf.set_font(use_f, 'B', 18) # หัวข้อใหญ่
    pdf.cell(0, 8, f"{d['my_comp']}", 0, 1, 'L')
    
    pdf.set_x(45)
    pdf.set_font(use_f, '', 14) # เนื้อหาทั่วไปปรับเป็น 14
    pdf.multi_cell(100, 6, f"{d['my_addr']}\nโทร: {d['my_tel']} แฟกซ์: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # กล่องเลขที่เอกสาร (ขวาบน)
    pdf.set_xy(140, 10)
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(55, 20, "", 1, 0) # กรอบ
    pdf.set_xy(142, 13)
    pdf.cell(50, 6, f"เลขที่: {d['doc_no']}", 0, 1, 'L')
    pdf.set_x(142)
    pdf.cell(50, 6, f"วันที่: {d['doc_date']}", 0, 1, 'L')

    # ชื่อเอกสาร (Title)
    pdf.set_y(45)
    pdf.set_font(use_f, 'B', 26)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # ข้อมูลลูกค้า และ เงื่อนไข
    pdf.set_y(60)
    start_y = pdf.get_y()
    
    # ซ้าย: ลูกค้า (ฟอนต์ใหญ่ขึ้น)
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(20, 7, "ลูกค้า:", 0, 0)
    pdf.set_font(use_f, '', 14)
    pdf.cell(0, 7, f"{d['c_name']}", 0, 1)
    
    pdf.set_x(15)
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(20, 7, "ผู้ติดต่อ:", 0, 0)
    pdf.set_font(use_f, '', 14)
    pdf.cell(0, 7, f"{d['contact']}", 0, 1)
    
    pdf.set_x(15)
    # multi_cell สำหรับที่อยู่
    pdf.multi_cell(110, 6, f"ที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']} แฟกซ์: {d['c_fax']}", 0, 'L')
    
    # ขวา: เงื่อนไข
    pdf.set_xy(135, start_y)
    pdf.multi_cell(65, 7, 
        f"กำหนดส่ง: {d['due_date']}\n"
        f"ยืนราคา: {d['valid_days']} วัน\n"
        f"เครดิต: {d['credit']} วัน\n"
        f"ครบกำหนด: {d['exp_date']}", 
        0, 'L')

    # --- ตารางสินค้า ---
    # *สำคัญ* 15 แถว เพื่อให้ฟอนต์ใหญ่ได้และไม่ล้นหน้า A4
    MAX_ROWS = 15 
    pdf.set_y(95)
    
    # กำหนดความกว้างคอลัมน์ (ปรับให้รวมกันได้ 180mm พอดีขอบ)
    cols_w = [12, 73, 15, 15, 25, 15, 25] 
    headers = ["ลำดับ", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    
    # หัวตาราง
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 13) # หัวตารางใหญ่ขึ้น
    for i, h in enumerate(headers):
        pdf.cell(cols_w[i], 9, h, 1, 0, 'C', True)
    pdf.ln()

    # Loop แสดงรายการ
    pdf.set_font(use_f, '', 13) # เนื้อหาในตารางใหญ่ขึ้น (13pt)
    row_height = 8 # ความสูงบรรทัดสินค้า
    
    valid_items = items_df[items_df['รายการ'].str.strip() != ""].copy()
    
    for i in range(MAX_ROWS):
        if i < len(valid_items):
            row = valid_items.iloc[i]
            q = to_num(row.get('จำนวน'))
            p = to_num(row.get('ราคา'))
            dis = to_num(row.get('ส่วนลด'))
            total = (q * p) - dis
            
            vals = [
                str(i+1),
                str(row.get('รายการ')),
                f"{q:,.0f}",
                str(row.get('หน่วย')),
                f"{p:,.2f}",
                f"{dis:,.2f}" if dis > 0 else "-",
                f"{total:,.2f}"
            ]
        else:
            # ตีตารางเปล่า
            vals = ["", "", "", "", "", "", ""]
        
        for j, txt in enumerate(vals):
            align = 'C'
            if j == 1: align = 'L'
            if j >= 4 and txt not in ["", "-"]: align = 'R'
            pdf.cell(cols_w[j], row_height, txt, 1, 0, align)
        pdf.ln()

    # --- สรุปยอดเงิน (แก้ไข: บีบระยะบรรทัดให้ชิดกัน) ---
    pdf.ln(5)
    current_y = pdf.get_y()
    
    # หมายเหตุ (ซ้าย) - ลดระยะห่างบรรทัดลงเหลือ 5
    pdf.set_xy(15, current_y)
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(0, 7, "หมายเหตุ / Remarks:", 0, 1)
    pdf.set_font(use_f, '', 13)
    pdf.multi_cell(100, 5, remark_text, 0, 'L') # <-- แก้ไข: ลด line-height เหลือ 5
    
    # ตัวเลข (ขวา) - บีบให้ชิดกัน
    sum_x_label = 135
    sum_x_val = 175
    sum_y = current_y
    
    def print_sum_row(label, value, bold=False, line=False):
        nonlocal sum_y
        pdf.set_xy(sum_x_label, sum_y)
        pdf.set_font(use_f, 'B' if bold else '', 13)
        pdf.cell(40, 6, label, 0, 0, 'R') # <-- แก้ไข: ลดความสูงช่องเหลือ 6
        pdf.set_xy(sum_x_val, sum_y)
        pdf.cell(25, 6, f"{value:,.2f}", 'B' if line else 0, 1, 'R') # <-- แก้ไข: ลดความสูงช่องเหลือ 6
        sum_y += 6 # <-- แก้ไข: เพิ่มระยะทีละ 6 พอ (เดิม 7)

    print_sum_row("รวมเงินสินค้า:", summary['gross'])
    print_sum_row("หักส่วนลด:", summary['discount'])
    print_sum_row("ยอดหลังหักส่วนลด:", summary['subtotal'])
    
    if show_vat_line:
        print_sum_row("ภาษีมูลค่าเพิ่ม 7%:", summary['vat'])
        
    print_sum_row("ยอดรวมทั้งสิ้น:", summary['grand_total'], True, True)

    # --- ลายเซ็น (แก้ไข: ย้ายลงล่างสุด ล่างสุดของหน้ากระดาษ) ---
    # ใช้ -35 เพื่อดันลงไปเกือบชิดขอบกระดาษ (ล่างสุดเท่าที่จะเป็นไปได้โดยไม่ตกขอบ)
    pdf.set_y(-25) 
    pdf.set_font(use_f, '', 13)
    
    sig_labels = ["ผู้สั่งซื้อสินค้า", "พนักงานขาย", "ผู้อนุมัติ"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    x_positions = [20, 85, 150]
    
    # เก็บค่า Y ปัจจุบันตรงโซนล่าง
    y_sig = pdf.get_y()
    
    for i in range(3):
        pdf.set_xy(x_positions[i], y_sig)
        pdf.cell(40, 6, "........................................", 0, 1, 'C')
        pdf.set_xy(x_positions[i], y_sig + 6)
        pdf.cell(40, 6, sig_labels[i], 0, 1, 'C')
        pdf.set_xy(x_positions[i], y_sig + 12)
        disp = f"({names[i]})" if names[i] else "(........................................)"
        pdf.cell(40, 6, disp, 0, 1, 'C')
        pdf.set_xy(x_positions[i], y_sig + 18)
        pdf.cell(40, 6, "วันที่ ...../...../..........", 0, 1, 'C')

    return bytes(pdf.output())

# ==========================================
# 4. USER INTERFACE (MAIN)
# ==========================================
def clear_all_data():
    st.session_state.grid_df = pd.DataFrame([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0.0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 15)
    reset_keys = ["c_name_in", "contact_in", "c_addr_in", "c_tel_in", "c_fax_in", "remark_in", "s1_in", "s2_in", "s3_in"]
    for k in reset_keys:
        if k in st.session_state: st.session_state[k] = ""
    st.session_state["cust_selector_tab1"] = "-- พิมพ์เอง --"
    st.toast("ล้างข้อมูลหน้าจอเรียบร้อย", icon="🗑️")

def update_customer_fields():
    sel = st.session_state.cust_selector_tab1
    if sel and sel != "-- พิมพ์เอง --":
        row = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == sel].iloc[0]
        st.session_state.c_name_in = str(row['ชื่อบริษัท'])
        st.session_state.contact_in = str(row['ผู้ติดต่อ']) if pd.notna(row['ผู้ติดต่อ']) else ""
        st.session_state.c_addr_in = str(row['ที่อยู่']) if pd.notna(row['ที่อยู่']) else ""
        st.session_state.c_tel_in = str(row['โทร']) if pd.notna(row['โทร']) else ""
        st.session_state.c_fax_in = str(row['แฟกซ์']) if pd.notna(row['แฟกซ์']) else ""

tab1, tab2, tab3, tab4 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า", "🗂️ ประวัติเอกสาร"])

# ------------------------------------------------------------------
# TAB 1: Quotation
# ------------------------------------------------------------------
with tab1:
    # Group 1: ข้อมูลผู้ขายและเอกสาร
    with st.container(border=True):
        st.subheader("🏢 ข้อมูลบริษัทและเอกสาร")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("ชื่อบริษัท", "บริษัท ศิวกิจ เทรดดิ้ง จำกัด", key="my_comp_in")
            st.text_input("ที่อยู่บริษัท", "123 ถนนตัวอย่าง กทม.", key="my_addr_in") 
            c1, c2, c3 = st.columns(3)
            with c1: st.text_input("โทรศัพท์", key="my_tel_in")        
            with c2: st.text_input("แฟกซ์", key="my_fax_in")        
            with c3: st.text_input("เลขผู้เสียภาษี", key="my_tax_in")
        
        with col2:
            st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d')}-001", key="doc_no_in")
            st.date_input("วันที่ออกเอกสาร", date.today(), key="doc_date_in")
            st.text_input("กำหนดส่ง", "ภายใน 7-15 วัน", key="due_date_in")
            
            r1, r2 = st.columns(2)
            with r1: st.text_input("ยืนราคา (วัน)", "30", key="valid_days_in")
            with r2: st.text_input("เครดิต (วัน)", "30", key="credit_in")

    st.write("---")

    # Group 2: ข้อมูลลูกค้า
    with st.container(border=True):
        c_h1, c_h2 = st.columns([1, 1])
        with c_h1: st.subheader("👤 ข้อมูลลูกค้า")
        with c_h2: 
            opts = ["-- พิมพ์เอง --"] + st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist()
            st.selectbox("📥 ดึงลูกค้าเก่า", opts, key="cust_selector_tab1", on_change=update_customer_fields)

        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.text_input("ชื่อบริษัทลูกค้า", key="c_name_in")
            st.text_input("ชื่อผู้ติดต่อ", key="contact_in")
            st.text_area("ที่อยู่จัดส่ง", height=70, key="c_addr_in")
        with c_col2:
            st.text_input("เบอร์โทรศัพท์", key="c_tel_in")
            st.text_input("เบอร์แฟกซ์", key="c_fax_in")

    st.write("---")

    # Group 3: ตารางสินค้า
    st.subheader("📦 รายการสินค้า")
    prod_opts = st.session_state.db_products['รหัสสินค้า'].astype(str).unique().tolist()
    
    edited_df = st.data_editor(
        st.session_state.grid_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัส", options=prod_opts, width="medium"),
            "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
            "จำนวน": st.column_config.NumberColumn("จำนวน", min_value=0.0, format="%.0f"),
            "ราคา": st.column_config.NumberColumn("ราคา", min_value=0.0, format="%.2f"),
            "ส่วนลด": st.column_config.NumberColumn("ส่วนลด", min_value=0.0, format="%.2f")
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_main"
    )

    # Auto-fill Logic
    needs_rerun = False
    for idx, row in edited_df.iterrows():
        code = str(row['รหัสสินค้า'])
        if code and code in prod_opts:
            info = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'] == code].iloc[0]
            if str(row['รายการ']) != info['รายการ']:
                edited_df.at[idx, 'รายการ'] = info['รายการ']
                edited_df.at[idx, 'หน่วย'] = info['หน่วย']
                edited_df.at[idx, 'ราคา'] = info['ราคา']
                needs_rerun = True
    
    if needs_rerun:
        st.session_state.grid_df = edited_df
        st.rerun()
    else:
        st.session_state.grid_df = edited_df

    # Calculation
    calc_df = edited_df.copy()
    calc_df['q'] = calc_df['จำนวน'].apply(to_num)
    calc_df['p'] = calc_df['ราคา'].apply(to_num)
    calc_df['d'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['total'] = (calc_df['q'] * calc_df['p']) - calc_df['d']
    
    sum_gross = (calc_df['q'] * calc_df['p']).sum()
    sum_disc = calc_df['d'].sum()
    sum_sub = calc_df['total'].sum()

    st.write("---")

    # Group 4: สรุปและปุ่ม
    f_col1, f_col2 = st.columns([1.5, 1])
    with f_col1:
        st.text_area("📝 หมายเหตุ", value="1. ราคายังไม่รวม VAT 7%\n2. กำหนดยืนราคา 30 วัน", key="remark_in", height=100)
        st.caption("ข้อมูลผู้ลงนาม")
        s1, s2, s3 = st.columns(3)
        with s1: st.text_input("ผู้สั่งซื้อ", key="s1_in")
        with s2: st.text_input("พนักงานขาย", key="s2_in")
        with s3: st.text_input("ผู้อนุมัติ", key="s3_in")

    with f_col2:
        has_vat = st.checkbox("คำนวณ VAT 7%", value=True)
        vat_val = sum_sub * 0.07 if has_vat else 0.0
        grand_total = sum_sub + vat_val
        
        vat_style = "" if has_vat else "display: none;"
        
        # HTML Display
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">ยอดรวมทั้งสิ้น (Grand Total)</div>
            <div class="metric-value">{grand_total:,.2f} บาท</div>
            <div style="margin-top: 15px; font-size: 0.9rem; color: #555; text-align: right; padding-right: 20px;">
                <table style="width: 100%;">
                    <tr><td style="text-align: left;">รวมสินค้า:</td><td style="text-align: right;">{sum_gross:,.2f}</td></tr>
                    <tr><td style="text-align: left;">ส่วนลด:</td><td style="text-align: right; color: red;">-{sum_disc:,.2f}</td></tr>
                    <tr><td style="text-align: left; font-weight: bold;">ก่อนภาษี:</td><td style="text-align: right; font-weight: bold;">{sum_sub:,.2f}</td></tr>
                    <tr style="{vat_style}"><td style="text-align: left;">VAT 7%:</td><td style="text-align: right;">{vat_val:,.2f}</td></tr>
                </table>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("###")
    
    b1, b2 = st.columns([0.3, 0.7])
    with b1:
        st.button("🧹 ล้างหน้าจอ", on_click=clear_all_data, use_container_width=True)
    with b2:
        if st.button("🚀 บันทึกและพิมพ์ PDF", type="primary", use_container_width=True):
            # 1. Save History
            doc_no = st.session_state.doc_no_in
            json_data = {
                "grid_df": edited_df.to_dict(),
                "doc_date_str": str(st.session_state.doc_date_in),
                "due_date": st.session_state.due_date_in,
                "valid_days": st.session_state.valid_days_in,
                "credit": st.session_state.credit_in,
                "c_name": st.session_state.c_name_in,
                "contact": st.session_state.contact_in,
                "c_addr": st.session_state.c_addr_in,
                "c_tel": st.session_state.c_tel_in,
                "c_fax": st.session_state.c_fax_in,
                "remark": st.session_state.remark_in,
                "s1": st.session_state.s1_in, "s2": st.session_state.s2_in, "s3": st.session_state.s3_in,
                "has_vat": has_vat
            }
            
            new_rec = {
                "ลบ": False,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "doc_no": doc_no,
                "customer": st.session_state.c_name_in,
                "total": grand_total,
                "data_json": json.dumps(json_data, ensure_ascii=False)
            }
            
            st.session_state.db_history = pd.concat([pd.DataFrame([new_rec]), st.session_state.db_history], ignore_index=True)
            save_data(st.session_state.db_history, HISTORY_FILE)
            
            # 2. Create PDF
            pdf_data = {
                "my_comp": st.session_state.my_comp_in, "my_addr": st.session_state.my_addr_in,
                "my_tel": st.session_state.my_tel_in, "my_fax": st.session_state.my_fax_in, "my_tax": st.session_state.my_tax_in,
                "doc_no": doc_no, "doc_date": st.session_state.doc_date_in.strftime("%d/%m/%Y"),
                "due_date": st.session_state.due_date_in,
                "valid_days": st.session_state.valid_days_in,
                "credit": st.session_state.credit_in,
                "exp_date": (st.session_state.doc_date_in + timedelta(days=int(st.session_state.valid_days_in) if st.session_state.valid_days_in.isdigit() else 30)).strftime("%d/%m/%Y"),
                "c_name": st.session_state.c_name_in, "contact": st.session_state.contact_in,
                "c_addr": st.session_state.c_addr_in, "c_tel": st.session_state.c_tel_in, "c_fax": st.session_state.c_fax_in
            }
            
            pdf_bytes = create_pdf(
                pdf_data, calc_df, 
                {"gross": sum_gross, "discount": sum_disc, "subtotal": sum_sub, "vat": vat_val, "grand_total": grand_total},
                {"s1": st.session_state.s1_in, "s2": st.session_state.s2_in, "s3": st.session_state.s3_in},
                st.session_state.remark_in, has_vat
            )
            
            st.success("✅ สร้างไฟล์เรียบร้อย!")
            st.download_button("📥 ดาวน์โหลด PDF", pdf_bytes, f"{doc_no}.pdf", "application/pdf", use_container_width=True)

# ------------------------------------------------------------------
# TAB 2: ลูกค้า
# ------------------------------------------------------------------
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    st.info("💡 วิธีใช้: แก้ไขข้อมูลในตาราง หรือติ๊ก 'ลบ' แล้วกดปุ่มบันทึกด้านล่าง (ปุ่มเดียวจบ)")
    
    with st.container(border=True):
        edited_customers = st.data_editor(
            st.session_state.db_customers, 
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True, 
            column_config={
                "ลบ": st.column_config.CheckboxColumn("ลบ (ติ๊กเพื่อลบ)", default=False, width="small"),
                "รหัส": st.column_config.TextColumn("รหัส", width="small"),
                "ชื่อบริษัท": st.column_config.TextColumn("ชื่อบริษัท", width="large", required=True),
            },
            key="cust_editor_v2"
        )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลง (ลูกค้า)", type="primary", use_container_width=True):
        saved_df = save_data(edited_customers, CUST_FILE, key_col="ชื่อบริษัท")
        st.session_state.db_customers = saved_df
        st.toast("✅ บันทึกและลบข้อมูลเรียบร้อย", icon="💾")
        st.rerun()

# ------------------------------------------------------------------
# TAB 3: สินค้า
# ------------------------------------------------------------------
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    st.info("💡 วิธีใช้: แก้ไขข้อมูลในตาราง หรือติ๊ก 'ลบ' แล้วกดปุ่มบันทึกด้านล่าง (ปุ่มเดียวจบ)")
    
    with st.container(border=True):
        edited_products = st.data_editor(
            st.session_state.db_products, 
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True, 
            column_config={
                "ลบ": st.column_config.CheckboxColumn("ลบ (ติ๊กเพื่อลบ)", default=False, width="small"),
                "รหัสสินค้า": st.column_config.TextColumn("รหัส", width="small", required=True),
                "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
                "ราคา": st.column_config.NumberColumn("ราคา", format="%.2f"),
            },
            key="prod_editor_v2"
        )
    
    if st.button("💾 บันทึกการเปลี่ยนแปลง (สินค้า)", type="primary", use_container_width=True):
        saved_df = save_data(edited_products, PROD_FILE, key_col="รหัสสินค้า")
        st.session_state.db_products = saved_df
        st.toast("✅ บันทึกและลบข้อมูลเรียบร้อย", icon="💾")
        st.rerun()

# ------------------------------------------------------------------
# TAB 4: ประวัติ
# ------------------------------------------------------------------
with tab4:
    st.header("🗂️ ประวัติใบเสนอราคา")
    
    if not st.session_state.db_history.empty:
        sel_hist = st.selectbox("เลือกเอกสารเพื่อแก้ไข", st.session_state.db_history['doc_no'].tolist())
        if st.button("🔄 โหลดข้อมูลกลับหน้าแรก", use_container_width=True):
            row = st.session_state.db_history[st.session_state.db_history['doc_no'] == sel_hist].iloc[0]
            data = json.loads(row['data_json'])
            
            st.session_state.grid_df = pd.DataFrame.from_dict(data['grid_df'])
            st.session_state.c_name_in = data.get('c_name', '')
            st.session_state.contact_in = data.get('contact', '')
            st.session_state.c_addr_in = data.get('c_addr', '')
            st.session_state.c_tel_in = data.get('c_tel', '')
            st.session_state.remark_in = data.get('remark', '')
            st.session_state.doc_no_in = row['doc_no']
            
            if 'doc_date_str' in data:
                try: st.session_state.doc_date_in = datetime.strptime(data['doc_date_str'], '%Y-%m-%d').date()
                except: pass
            
            st.toast(f"โหลดข้อมูล {sel_hist} เรียบร้อย ไปที่ Tab 1 ได้เลย", icon="🔄")
            
        st.divider()
        
        edited_hist = st.data_editor(
            st.session_state.db_history,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ลบ": st.column_config.CheckboxColumn("ลบ (ติ๊กเพื่อลบ)", default=False),
                "timestamp": st.column_config.TextColumn("เวลาบันทึก", disabled=True),
                "doc_no": st.column_config.TextColumn("เลขที่", disabled=True),
                "total": st.column_config.NumberColumn("ยอดรวม", format="%.2f", disabled=True),
                "data_json": None
            },
            key="hist_editor"
        )
        
        if st.button("💾 อัปเดตประวัติ", type="primary", use_container_width=True):
            saved_hist = save_data(edited_hist, HISTORY_FILE)
            st.session_state.db_history = saved_hist
            st.toast("✅ อัปเดตประวัติเรียบร้อย", icon="💾")
            st.rerun()
    else:
        st.info("ยังไม่มีประวัติ")
