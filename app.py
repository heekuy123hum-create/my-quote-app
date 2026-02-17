import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import json
from fpdf import FPDF
import requests
from streamlit_lottie import st_lottie
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from bahttext import bahttext 

# ==========================================
# 1. SYSTEM CONFIG & ASSETS
# ==========================================
st.set_page_config(page_title="SIWAKIT TRADING SYSTEM", layout="wide", page_icon="🏢")

# --- CSS ตกแต่ง UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Prompt', sans-serif;
        background-color: #f8f9fa;
    }
    
    /* Header Styling */
    h1 {
        color: #1e3a8a;
        font-weight: 700;
        font-size: 2.2rem;
    }
    h2, h3 {
        color: #334155;
        font-weight: 600;
    }

    /* Custom Cards */
    .custom-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
    }
    
    /* Input Fields Styling */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
    }
    .stSelectbox > div > div > div {
        border-radius: 8px;
    }

    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Metric Card (ใบเสร็จ) */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
        border: 1px solid #bbf7d0;
        padding: 25px;
        border-radius: 15px;
        color: #166534;
        text-align: right;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: "฿";
        position: absolute;
        top: -20px;
        left: -20px;
        font-size: 8rem;
        color: rgba(34, 197, 94, 0.1);
        font-weight: bold;
    }
    .metric-label {
        font-size: 1rem;
        margin-bottom: 5px;
        font-weight: 600;
        color: #15803d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        color: #15803d;
        text-shadow: 2px 2px 0px rgba(255,255,255,1);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 10px 10px 0 0;
        border: 1px solid #e2e8f0;
        border-bottom: none;
        padding: 0 20px;
        color: #334155; 
    }
    .stTabs [aria-selected="true"] {
        background-color: #fff;
        border-top: 3px solid #3b82f6;
        color: #3b82f6;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Lottie Animation Loader ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

lottie_office = load_lottieurl("https://lottie.host/5a8b7928-8924-4069-950c-1123533866b1/0XgV0lK1uF.json")
lottie_success = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_ttv8K8.json")

# ชื่อไฟล์สำหรับเก็บข้อมูล
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"
HISTORY_FILE = "history_quotes.csv"
FONT_PATH = "THSarabunNew.ttf" 

# เริ่มต้นตัวแปร Session State
if "grid_df" not in st.session_state:
    st.session_state.grid_df = pd.DataFrame(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 15
    )
if "generated_pdf_bytes" not in st.session_state:
    st.session_state.generated_pdf_bytes = None
if "last_doc_no" not in st.session_state:
    st.session_state.last_doc_no = ""

# ==========================================
# 2. EMAIL SYSTEM FUNCTION
# ==========================================
def send_email_with_attachment(sender_email, sender_password, receiver_email, subject, body, file_bytes, filename):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        return True, "ส่งอีเมลสำเร็จ!"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาด: {str(e)}"

# ==========================================
# 3. DATABASE & LOGIC MANAGEMENT
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
                {"ลบ": False, "รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง", "ราคา": 1000, "หน่วย": "ชิ้น"}
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
    df_to_save = df.copy()
    if 'ลบ' in df_to_save.columns:
        df_to_save = df_to_save[df_to_save['ลบ'] == False]
        df_to_save['ลบ'] = False
    if key_col and key_col in df_to_save.columns:
         df_to_save = df_to_save[df_to_save[key_col].astype(str).str.strip() != ""]
    if 'Unnamed: 0' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['Unnamed: 0'])
    df_to_save = df_to_save.reset_index(drop=True)
    df_to_save.to_csv(filename, index=False, encoding='utf-8-sig')
    return df_to_save

def to_int(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return int(round(float(val))) if val is not None else 0
    except:
        return 0

# --- Function Auto-Increment Doc No ---
def generate_doc_no():
    # 1. สร้าง Prefix ของวันนี้
    today_str = datetime.now().strftime('%Y%m%d')
    prefix = f"QT-{today_str}"
    
    # 2. ถ้าไม่มีประวัติเลย ให้เริ่มที่ 001
    if st.session_state.db_history.empty:
        return f"{prefix}-001"
    
    # 3. ค้นหาเอกสารที่มี Prefix เดียวกันในประวัติ
    # แปลงคอลัมน์ doc_no เป็น string ให้แน่ใจ
    hist_df = st.session_state.db_history.copy()
    hist_df['doc_no'] = hist_df['doc_no'].astype(str)
    
    matched_docs = hist_df[hist_df['doc_no'].str.contains(prefix, na=False)]
    
    if matched_docs.empty:
        return f"{prefix}-001"
    
    # 4. หาเลขรันสูงสุดแล้วบวก 1
    max_run = 0
    for doc in matched_docs['doc_no']:
        try:
            # สมมติ format คือ QT-YYYYMMDD-XXX
            parts = doc.split('-')
            if len(parts) >= 3:
                run_num = int(parts[-1])
                if run_num > max_run:
                    max_run = run_num
        except:
            pass
            
    return f"{prefix}-{max_run + 1:03d}"

load_data()

# ==========================================
# 4. PDF ENGINE (แก้ไข: จัดรูปแบบตามคำขอ)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)
    
    # Prepare Font
    if os.path.exists(FONT_PATH):
        pdf.add_font('THSarabun', '', FONT_PATH, uni=True)
        pdf.add_font('THSarabun', 'B', FONT_PATH, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # --- Prepare Data for Pagination ---
    # Filter only valid items
    valid_items = items_df[items_df['รายการ'].str.strip() != ""].copy()
    
    # Constants
    MAX_ROWS_PER_PAGE = 15
    total_items = len(valid_items)
    
    # Calculate pages needed (at least 1 page)
    import math
    num_pages = math.ceil(total_items / MAX_ROWS_PER_PAGE)
    if num_pages == 0: num_pages = 1
    
    # Loop generate pages
    for page in range(num_pages):
        pdf.add_page()
        
        # --- HEADER (Draw on every page) ---
        # Logo
        for ext in ['png', 'jpg', 'jpeg']:
            if os.path.exists(f"logo.{ext}"):
                pdf.image(f"logo.{ext}", x=15, y=10, w=25)
                break
                
        pdf.set_xy(45, 10)
        pdf.set_font(use_f, 'B', 18)
        pdf.cell(0, 8, f"{d['my_comp']}", 0, 1, 'L')
        
        pdf.set_x(45)
        pdf.set_font(use_f, '', 14)
        pdf.multi_cell(100, 6, f"{d['my_addr']}\nโทร: {d['my_tel']} แฟกซ์: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

        # Doc No Box
        pdf.set_xy(140, 10)
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(55, 20, "", 1, 0)
        pdf.set_xy(142, 13)
        pdf.cell(50, 6, f"เลขที่: {d['doc_no']}", 0, 1, 'L')
        pdf.set_x(142)
        pdf.cell(50, 6, f"วันที่: {d['doc_date']}", 0, 1, 'L')
        # Show Page No
        pdf.set_xy(142, 25)
        pdf.set_font(use_f, '', 12)
        pdf.cell(50, 4, f"หน้า {page+1} / {num_pages}", 0, 1, 'R')

        # Title
        pdf.set_y(45)
        pdf.set_font(use_f, 'B', 26)
        pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

        # Customer Info (แก้ไข: ทำให้ข้อมูลติดกับหัวข้อ)
        pdf.set_y(60)
        start_y = pdf.get_y()
        
        # ใช้สตริงเดียวเพื่อให้ชิดกันเหมือนที่อยู่/โทร
        pdf.set_font(use_f, '', 14)
        # Bold label part manual simulation implies just printing the whole line
        # But to make label bold and value normal needs split. 
        # เพื่อความง่ายและแน่นตามคำขอ ผมจะพิมพ์เป็นบรรทัดเดียวกันเลย
        
        # ลูกค้า
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(15, 7, "ลูกค้า: ", 0, 0)
        pdf.set_font(use_f, '', 14)
        pdf.cell(0, 7, f"{d['c_name']}", 0, 1)
        
        # ผู้ติดต่อ
        pdf.set_x(15)
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(20, 7, "ผู้ติดต่อ: ", 0, 0)
        pdf.set_font(use_f, '', 14)
        pdf.cell(0, 7, f"{d['contact']}", 0, 1)
        
        # ที่อยู่ / โทร / แฟกซ์ (เดิมดีอยู่แล้ว)
        pdf.set_x(15)
        pdf.multi_cell(110, 6, f"ที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']} แฟกซ์: {d['c_fax']}", 0, 'L')
        
        pdf.set_xy(135, start_y)
        pdf.multi_cell(65, 7, 
            f"กำหนดส่ง: {d['due_date']}\n"
            f"ยืนราคา: {d['valid_days']} วัน\n"
            f"เครดิต: {d['credit']} วัน\n"
            f"ครบกำหนด: {d['exp_date']}", 
            0, 'L')

        # --- TABLE ---
        pdf.set_y(95)
        cols_w = [12, 73, 15, 15, 25, 15, 25] 
        headers = ["ลำดับ", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font(use_f, 'B', 13)
        for i, h in enumerate(headers):
            pdf.cell(cols_w[i], 9, h, 1, 0, 'C', True)
        pdf.ln()

        pdf.set_font(use_f, '', 13)
        row_height = 8 
        
        # Slice items for this page
        start_idx = page * MAX_ROWS_PER_PAGE
        end_idx = start_idx + MAX_ROWS_PER_PAGE
        page_items = valid_items.iloc[start_idx:end_idx]
        
        rows_to_print = MAX_ROWS_PER_PAGE 
        
        for i in range(rows_to_print):
            # Calculate actual item index
            current_item_idx = start_idx + i
            
            if i < len(page_items):
                row = page_items.iloc[i]
                q = to_int(row.get('จำนวน'))
                p = to_int(row.get('ราคา'))
                dis = to_int(row.get('ส่วนลด'))
                total = int(round((q * p) - dis))
                
                vals = [
                    str(current_item_idx + 1),
                    str(row.get('รายการ')),
                    f"{q:,.0f}",
                    str(row.get('หน่วย')),
                    f"{p:,.0f}",
                    f"{dis:,.0f}" if dis > 0 else "-",
                    f"{total:,.0f}"
                ]
            else:
                vals = ["", "", "", "", "", "", ""]
            
            for j, txt in enumerate(vals):
                align = 'C' # Default Center ตามคำขอ
                if j == 1: align = 'L' # ชื่อสินค้า ชิดซ้าย
                # เอาเงื่อนไข j >= 4 align='R' ออก เพื่อให้ ราคา/ส่วนลด/รวม เป็น Center
                
                pdf.cell(cols_w[j], row_height, txt, 1, 0, align)
            pdf.ln()

        # --- SUMMARY (Only on Last Page) ---
        if page == num_pages - 1:
            pdf.ln(5)
            current_y = pdf.get_y()
            
            # --- ส่วนหมายเหตุ (อยู่ซ้าย) ---
            pdf.set_xy(15, current_y)
            pdf.set_font(use_f, 'B', 14)
            pdf.cell(0, 7, "หมายเหตุ / Remarks:", 0, 1)
            pdf.set_font(use_f, '', 13)
            pdf.multi_cell(100, 5, remark_text, 0, 'L')
            
            # --- ส่วนตัวเลขสรุป (อยู่ขวา) ---
            sum_x_label = 135
            sum_x_val = 175
            sum_y = current_y
            
            def print_sum_row(label, value, bold=False, line=False):
                nonlocal sum_y
                pdf.set_xy(sum_x_label, sum_y)
                pdf.set_font(use_f, 'B' if bold else '', 13)
                pdf.cell(40, 6, label, 0, 0, 'R')
                pdf.set_xy(sum_x_val, sum_y)
                pdf.cell(25, 6, f"{value:,.0f}", 'B' if line else 0, 1, 'R')
                sum_y += 6

            print_sum_row("รวมเงินสินค้า:", summary['gross'])
            print_sum_row("หักส่วนลด:", summary['discount'])
            print_sum_row("ยอดหลังหักส่วนลด:", summary['subtotal'])
            
            if show_vat_line:
                print_sum_row("ภาษีมูลค่าเพิ่ม 7%:", summary['vat'])
                
            print_sum_row("ยอดรวมทั้งสิ้น:", summary['grand_total'], True, True)

            # --- ย้าย BAHT TEXT มาไว้ตรงนี้ (ใต้ตัวเลขสรุปฝั่งขวา) ---
            grand_total_val = summary['grand_total']
            baht_text_str = bahttext(grand_total_val)
            
            pdf.set_xy(sum_x_label - 20, sum_y + 1) # ขยับตำแหน่งเล็กน้อย
            pdf.set_font(use_f, '', 13) # ขนาดตัวอักษรเท่ากับตัวเลข (13)
            # จัดชิดขวาเพื่อให้ดูสวยงามใต้ตัวเลข หรือจัดกลาง relative กับ block
            pdf.cell(85, 6, f"({baht_text_str})", 0, 1, 'R')

            # Signatures
            pdf.set_y(-35) 
            pdf.set_font(use_f, '', 13)
            
            sig_labels = ["ผู้สั่งซื้อสินค้า", "พนักงานขาย", "ผู้อนุมัติ"]
            names = [sigs['s1'], sigs['s2'], sigs['s3']]
            x_positions = [20, 85, 150]
            
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
# 5. USER INTERFACE
# ==========================================
def clear_all_data():
    st.session_state.grid_df = pd.DataFrame([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 15)
    reset_keys = ["c_name_in", "contact_in", "c_addr_in", "c_tel_in", "c_fax_in", "remark_in", "s1_in", "s2_in", "s3_in"]
    for k in reset_keys:
        if k in st.session_state: st.session_state[k] = ""
    st.session_state["cust_selector_tab1"] = "-- พิมพ์เอง --"
    st.session_state.generated_pdf_bytes = None
    # Reset Doc No to new auto increment
    st.session_state.doc_no_in = generate_doc_no() 
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

# --- SIDEBAR: Email Settings ---
with st.sidebar:
    st.markdown("### ⚙️ Control Panel")
    with st.expander("📧 ตั้งค่าอีเมล (SMTP)", expanded=False):
        st.info("สำหรับ Gmail ต้องใช้ App Password")
        email_sender = st.text_input("อีเมลผู้ส่ง (Sender)", placeholder="your@gmail.com")
        email_password = st.text_input("รหัสผ่านแอพ (App Password)", type="password")
    
    st.divider()
    st.caption("© 2024 Siwakit Trading System v2.0")

# --- MAIN HEADER with Layout ---
st.markdown('<div style="padding-bottom: 20px;">', unsafe_allow_html=True)
col_head1, col_head2 = st.columns([0.7, 0.3])
with col_head1:
    st.title("SIWAKIT TRADING")
    st.markdown("#### 🏢 ระบบออกใบเสนอราคาและจัดการฐานข้อมูล")
with col_head2:
    if lottie_office:
        st_lottie(lottie_office, height=120, key="header_lottie")
st.markdown('</div>', unsafe_allow_html=True)

# Tabs Navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 สร้างใบเสนอราคา (Quotation)", 
    "👥 ฐานข้อมูลลูกค้า (Customers)", 
    "📦 ฐานข้อมูลสินค้า (Products)", 
    "🗂️ ประวัติเอกสาร (History)"
])

# ------------------------------------------------------------------
# TAB 1: Quotation (UI REVAMP)
# ------------------------------------------------------------------
with tab1:
    # 1. Header Info Section (Seller + Doc Info)
    with st.container(border=True):
        st.markdown("##### 🧾 ข้อมูลเอกสารและผู้ขาย (Document Info)")
        c1, c2 = st.columns([1.5, 1])
        with c1:
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.text_input("ชื่อบริษัทผู้ขาย", "บริษัท ศิวกิจ เทรดดิ้ง จำกัด", key="my_comp_in")
                st.text_input("โทรศัพท์", key="my_tel_in")
            with col_s2:
                st.text_input("ที่อยู่บริษัท", "123 ถนนตัวอย่าง กทม.", key="my_addr_in")
                st.text_input("เลขผู้เสียภาษี", key="my_tax_in")
                st.text_input("แฟกซ์", key="my_fax_in") 
                
        with c2:
            st.markdown("""<div style="background-color:#eff6ff; padding:15px; border-radius:10px;">""", unsafe_allow_html=True)
            dc1, dc2 = st.columns(2)
            with dc1:
                # ใช้ Function generate_doc_no() เป็นค่า default
                st.text_input("เลขที่ใบเสนอราคา", value=generate_doc_no(), key="doc_no_in")
                st.text_input("ยืนราคา (วัน)", "30", key="valid_days_in")
            with dc2:
                st.date_input("วันที่เอกสาร", date.today(), key="doc_date_in")
                st.text_input("เครดิต (วัน)", "30", key="credit_in")
            
            st.text_input("กำหนดส่งสินค้า", "ภายใน 7-15 วัน", key="due_date_in")
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. Customer Info Section
    with st.container(border=True):
        # Header Row for Customer
        cust_h1, cust_h2 = st.columns([0.6, 0.4])
        with cust_h1: 
            st.markdown("##### 👤 ข้อมูลลูกค้า (Customer Details)")
        with cust_h2: 
            # Dropdown เลือกลูกค้า
            opts = ["-- พิมพ์เอง --"] + st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist()
            st.selectbox("🔍 ค้นหาลูกค้าเก่า", opts, key="cust_selector_tab1", on_change=update_customer_fields, label_visibility="collapsed")

        # Customer Fields
        cc1, cc2, cc3 = st.columns([1.5, 1, 1])
        with cc1:
            st.text_input("ชื่อบริษัทลูกค้า", key="c_name_in", placeholder="ระบุชื่อบริษัท...")
            st.text_area("ที่อยู่จัดส่ง", height=109, key="c_addr_in", placeholder="ที่อยู่...")
        with cc2:
            st.text_input("ผู้ติดต่อ", key="contact_in", placeholder="ชื่อผู้ติดต่อ...")
            st.text_input("เบอร์โทรศัพท์", key="c_tel_in")
        with cc3:
            st.write("") 
            st.write("") 
            st.write("") 
            st.text_input("เบอร์แฟกซ์", key="c_fax_in")

    # 3. Items Table
    st.markdown("##### 📦 รายการสินค้า (Items)")
    
    prod_opts = st.session_state.db_products['รหัสสินค้า'].astype(str).unique().tolist()
    
    edited_df = st.data_editor(
        st.session_state.grid_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัส", options=prod_opts, width="medium"),
            "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
            # Format เป็นจำนวนเต็ม (%.0f)
            "จำนวน": st.column_config.NumberColumn("จำนวน", min_value=0, format="%.0f"),
            "ราคา": st.column_config.NumberColumn("ราคา", min_value=0, format="%.0f"),
            "ส่วนลด": st.column_config.NumberColumn("ส่วนลด", min_value=0, format="%.0f")
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
                edited_df.at[idx, 'ราคา'] = int(info['ราคา']) # cast to int
                needs_rerun = True
    
    if needs_rerun:
        st.session_state.grid_df = edited_df
        st.rerun()
    else:
        st.session_state.grid_df = edited_df

    # Calculation Logic (Integer Version)
    calc_df = edited_df.copy()
    calc_df['q'] = calc_df['จำนวน'].apply(to_int)
    calc_df['p'] = calc_df['ราคา'].apply(to_int)
    calc_df['d'] = calc_df['ส่วนลด'].apply(to_int)
    # คำนวณทีละบรรทัดปัดเป็น int ทันที
    calc_df['total'] = calc_df.apply(lambda x: int(round((x['q'] * x['p']) - x['d'])), axis=1)
    
    sum_gross = int((calc_df['q'] * calc_df['p']).sum())
    sum_disc = int(calc_df['d'].sum())
    sum_sub = int(calc_df['total'].sum())

    st.write("---")

    # 4. Summary & Actions
    f_col1, f_col2 = st.columns([1.8, 1])
    
    with f_col1:
        st.markdown("##### 📝 หมายเหตุ & การอนุมัติ")
        st.text_area("หมายเหตุ (Remarks)", value="1. ราคายังไม่รวม VAT 7%\n2. กำหนดยืนราคา 30 วัน", key="remark_in", height=100, label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        with s1: st.text_input("ผู้สั่งซื้อ", key="s1_in")
        with s2: st.text_input("พนักงานขาย", key="s2_in")
        with s3: st.text_input("ผู้อนุมัติ", key="s3_in")

    with f_col2:
        # Grand Total Card
        has_vat = st.checkbox("คำนวณ VAT 7%", value=True)
        # คำนวณ VAT แล้วปัดเป็น int
        vat_val = int(round(sum_sub * 0.07)) if has_vat else 0
        grand_total = sum_sub + vat_val
        
        # แปลงเป็นตัวหนังสือไทยเพื่อโชว์หน้าจอ (Optional)
        baht_text_show = bahttext(grand_total)
        
        vat_style = "" if has_vat else "display: none;"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">ยอดรวมทั้งสิ้น (Grand Total)</div>
            <div class="metric-value">{grand_total:,.0f}</div>
            <div style="font-size: 0.8rem; color: #166534; opacity: 0.8; margin-bottom:10px;">{baht_text_show}</div>
            <div style="margin-top: 15px; font-size: 0.9rem; color: #555; text-align: right; border-top: 1px dashed #ccc; padding-top:10px;">
                <table style="width: 100%;">
                    <tr><td style="text-align: left; color:#666;">รวมสินค้า:</td><td style="text-align: right;">{sum_gross:,.0f}</td></tr>
                    <tr><td style="text-align: left; color:#666;">ส่วนลด:</td><td style="text-align: right; color: #dc2626;">-{sum_disc:,.0f}</td></tr>
                    <tr><td style="text-align: left; font-weight: 600;">ก่อนภาษี:</td><td style="text-align: right; font-weight: 600;">{sum_sub:,.0f}</td></tr>
                    <tr style="{vat_style}"><td style="text-align: left; color:#666;">VAT 7%:</td><td style="text-align: right;">{vat_val:,.0f}</td></tr>
                </table>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("###")
    
    # Action Buttons
    b1, b2 = st.columns([0.2, 0.8])
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
            
            st.session_state.generated_pdf_bytes = pdf_bytes
            st.session_state.last_doc_no = doc_no
            st.success("✅ บันทึกข้อมูลเรียบร้อย!")
            st.rerun()

    # --- ส่วน Download / Email ---
    if st.session_state.generated_pdf_bytes is not None:
        st.divider()
        st.markdown(f"#### 🚀 จัดการเอกสาร: `{st.session_state.last_doc_no}`")
        
        with st.container(border=True):
            act_col1, act_col2 = st.columns(2)
            with act_col1:
                st.download_button(
                    label="📄 ดาวน์โหลด PDF",
                    data=st.session_state.generated_pdf_bytes,
                    file_name=f"Quotation_{st.session_state.last_doc_no}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            
            with act_col2:
                with st.popover("📧 ส่งอีเมลหาลูกค้า", use_container_width=True):
                    st.markdown("##### ส่งอีเมลพร้อมไฟล์ PDF")
                    receiver_mail = st.text_input("อีเมลปลายทาง", placeholder="customer@example.com")
                    subject_mail = st.text_input("หัวข้ออีเมล", value=f"ใบเสนอราคา: {st.session_state.last_doc_no}")
                    body_mail = st.text_area("ข้อความ", value="เรียน คุณลูกค้า\n\nแนบไฟล์ใบเสนอราคาครับ\n\nขอบคุณครับ")
                    
                    if st.button("ส่งอีเมลทันที"):
                        if not email_sender or not email_password:
                            st.error("กรุณาตั้งค่าอีเมลใน Sidebar ก่อน")
                        elif not receiver_mail:
                            st.error("กรุณาระบุอีเมลปลายทาง")
                        else:
                            with st.spinner("กำลังส่งอีเมล..."):
                                success, msg = send_email_with_attachment(
                                    email_sender, email_password, receiver_mail, 
                                    subject_mail, body_mail, 
                                    st.session_state.generated_pdf_bytes, 
                                    f"Quotation_{st.session_state.last_doc_no}.pdf"
                                )
                                if success:
                                    st.success(msg)
                                else:
                                    st.error(msg)

# ------------------------------------------------------------------
# TAB 2: Customer Database
# ------------------------------------------------------------------
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    
    # Form เพิ่มลูกค้า
    with st.expander("➕ เพิ่ม/แก้ไข ลูกค้า", expanded=False):
        c_id = st.text_input("รหัสลูกค้า", "")
        c_n = st.text_input("ชื่อบริษัท/ลูกค้า", "")
        c_p = st.text_input("ผู้ติดต่อ (Contact)", "")
        c_a = st.text_area("ที่อยู่", "")
        c_t = st.text_input("เบอร์โทร", "")
        c_f = st.text_input("แฟกซ์", "")
        
        if st.button("บันทึกข้อมูลลูกค้า"):
            if c_n:
                new_row = {"ลบ": False, "รหัส": c_id, "ชื่อบริษัท": c_n, "ผู้ติดต่อ": c_p, "ที่อยู่": c_a, "โทร": c_t, "แฟกซ์": c_f}
                st.session_state.db_customers = pd.concat([st.session_state.db_customers, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.db_customers, CUST_FILE)
                st.success("บันทึกสำเร็จ!")
                st.rerun()
            else:
                st.error("กรุณากรอกชื่อบริษัท")

    # Table Display
    edit_cust = st.data_editor(
        st.session_state.db_customers,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_cust"
    )
    
    if st.button("💾 บันทึกการแก้ไข (ลูกค้า)"):
        st.session_state.db_customers = save_data(edit_cust, CUST_FILE, "ชื่อบริษัท")
        st.success("อัพเดทฐานข้อมูลเรียบร้อย")
        st.rerun()

# ------------------------------------------------------------------
# TAB 3: Product Database
# ------------------------------------------------------------------
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    
    with st.expander("➕ เพิ่มสินค้าใหม่", expanded=False):
        p_code = st.text_input("รหัสสินค้า", "")
        p_name = st.text_input("ชื่อสินค้า", "")
        p_price = st.number_input("ราคามาตรฐาน", min_value=0.0)
        p_unit = st.text_input("หน่วยนับ", "ชิ้น")
        
        if st.button("บันทึกสินค้า"):
            if p_code and p_name:
                new_p = {"ลบ": False, "รหัสสินค้า": p_code, "รายการ": p_name, "ราคา": p_price, "หน่วย": p_unit}
                st.session_state.db_products = pd.concat([st.session_state.db_products, pd.DataFrame([new_p])], ignore_index=True)
                save_data(st.session_state.db_products, PROD_FILE)
                st.success("เพิ่มสินค้าสำเร็จ!")
                st.rerun()
            else:
                st.error("กรุณากรอกรหัสและชื่อสินค้า")

    edit_prod = st.data_editor(
        st.session_state.db_products,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_prod"
    )
    
    if st.button("💾 บันทึกการแก้ไข (สินค้า)"):
        st.session_state.db_products = save_data(edit_prod, PROD_FILE, "รหัสสินค้า")
        st.success("อัพเดทสินค้าเรียบร้อย")
        st.rerun()

# ------------------------------------------------------------------
# TAB 4: History
# ------------------------------------------------------------------
with tab4:
    st.header("🗂️ ประวัติใบเสนอราคา")
    
    # Filter
    search_q = st.text_input("🔍 ค้นหาเลขที่เอกสาร หรือ ชื่อลูกค้า", "")
    
    df_show = st.session_state.db_history.copy()
    if search_q:
        df_show = df_show[
            df_show['doc_no'].str.contains(search_q, case=False, na=False) | 
            df_show['customer'].str.contains(search_q, case=False, na=False)
        ]
    
    # Sort by timestamp desc
    if not df_show.empty:
        df_show = df_show.sort_values(by="timestamp", ascending=False)

    for index, row in df_show.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([1.5, 2, 1, 1])
            with col1:
                st.markdown(f"**{row['doc_no']}**")
                st.caption(f"📅 {row['timestamp']}")
            with col2:
                st.write(f"🏢 {row['customer']}")
            with col3:
                st.write(f"💰 {row['total']:,.2f}")
            with col4:
                if st.button("📄 ดู/พิมพ์", key=f"btn_reprint_{index}"):
                    # Load JSON back to create PDF
                    try:
                        data = json.loads(row['data_json'])
                        # Re-calculate totals
                        r_grid_df = pd.DataFrame(data['grid_df'])
                        r_calc_df = r_grid_df.copy()
                        r_calc_df['q'] = r_calc_df['จำนวน'].apply(to_int)
                        r_calc_df['p'] = r_calc_df['ราคา'].apply(to_int)
                        r_calc_df['d'] = r_calc_df['ส่วนลด'].apply(to_int)
                        r_calc_df['total'] = r_calc_df.apply(lambda x: int(round((x['q'] * x['p']) - x['d'])), axis=1)
                        
                        r_sum_gross = int((r_calc_df['q'] * r_calc_df['p']).sum())
                        r_sum_disc = int(r_calc_df['d'].sum())
                        r_sum_sub = int(r_calc_df['total'].sum())
                        has_vat = data.get('has_vat', True)
                        r_vat_val = int(round(r_sum_sub * 0.07)) if has_vat else 0
                        r_grand_total = r_sum_sub + r_vat_val
                        
                        pdf_data = {
                            "my_comp": st.session_state.my_comp_in, "my_addr": st.session_state.my_addr_in,
                            "my_tel": st.session_state.my_tel_in, "my_fax": st.session_state.my_fax_in, "my_tax": st.session_state.my_tax_in,
                            "doc_no": row['doc_no'], 
                            "doc_date": datetime.strptime(data['doc_date_str'], "%Y-%m-%d").strftime("%d/%m/%Y") if 'doc_date_str' in data else "-",
                            "due_date": data.get('due_date', '-'),
                            "valid_days": data.get('valid_days', '30'),
                            "credit": data.get('credit', '30'),
                            "exp_date": "-", # ขี้เกียจคำนวณย้อนหลัง ให้ใส่ - ไปก่อน หรือคำนวณใหม่ได้
                            "c_name": data.get('c_name', '-'), "contact": data.get('contact', '-'),
                            "c_addr": data.get('c_addr', '-'), "c_tel": data.get('c_tel', '-'), "c_fax": data.get('c_fax', '-')
                        }
                        
                        # Re-calc Exp Date
                        try:
                            d_date = datetime.strptime(data['doc_date_str'], "%Y-%m-%d")
                            days = int(data.get('valid_days', 30))
                            pdf_data['exp_date'] = (d_date + timedelta(days=days)).strftime("%d/%m/%Y")
                        except:
                            pass

                        pdf_bytes = create_pdf(
                            pdf_data, r_calc_df, 
                            {"gross": r_sum_gross, "discount": r_sum_disc, "subtotal": r_sum_sub, "vat": r_vat_val, "grand_total": r_grand_total},
                            {"s1": data.get('s1', ''), "s2": data.get('s2', ''), "s3": data.get('s3', '')},
                            data.get('remark', ''), has_vat
                        )
                        st.session_state.generated_pdf_bytes = pdf_bytes
                        st.session_state.last_doc_no = row['doc_no']
                        st.toast(f"โหลดเอกสาร {row['doc_no']} เรียบร้อย", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading: {e}")
