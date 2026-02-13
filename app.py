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

# ==========================================
# 1. SYSTEM CONFIG & ASSETS
# ==========================================
st.set_page_config(page_title="SIWAKIT TRADING SYSTEM", layout="wide", page_icon="🏢")

# --- CSS ตกแต่ง UI (แก้ไขเรื่อง Tab มองไม่เห็นตัวหนังสือ) ---
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
    
    /* Tab Styling (จุดที่แก้ไข) */
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
        color: #334155; /* เพิ่มบรรทัดนี้: บังคับให้ตัวหนังสือสีเข้ม จะได้มองเห็นบนพื้นขาว */
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

# โหลด Animation
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
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0.0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 15
    )
if "generated_pdf_bytes" not in st.session_state:
    st.session_state.generated_pdf_bytes = None
if "last_doc_no" not in st.session_state:
    st.session_state.last_doc_no = ""

# ==========================================
# 2. EMAIL SYSTEM FUNCTION (คงเดิม)
# ==========================================
def send_email_with_attachment(sender_email, sender_password, receiver_email, subject, body, file_bytes, filename):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

        # SMTP Server (Default Gmail)
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
# 3. DATABASE MANAGEMENT (คงเดิม)
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

def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val is not None else 0.0
    except:
        return 0.0

load_data()

# ==========================================
# 4. PDF ENGINE (คงเดิม ตามสั่ง)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    if os.path.exists(FONT_PATH):
        pdf.add_font('THSarabun', '', FONT_PATH, uni=True)
        pdf.add_font('THSarabun', 'B', FONT_PATH, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # Header
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

    # Title
    pdf.set_y(45)
    pdf.set_font(use_f, 'B', 26)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # Customer Info
    pdf.set_y(60)
    start_y = pdf.get_y()
    
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
    pdf.multi_cell(110, 6, f"ที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']} แฟกซ์: {d['c_fax']}", 0, 'L')
    
    pdf.set_xy(135, start_y)
    pdf.multi_cell(65, 7, 
        f"กำหนดส่ง: {d['due_date']}\n"
        f"ยืนราคา: {d['valid_days']} วัน\n"
        f"เครดิต: {d['credit']} วัน\n"
        f"ครบกำหนด: {d['exp_date']}", 
        0, 'L')

    # Table
    MAX_ROWS = 15 
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
            vals = ["", "", "", "", "", "", ""]
        
        for j, txt in enumerate(vals):
            align = 'C'
            if j == 1: align = 'L'
            if j >= 4 and txt not in ["", "-"]: align = 'R'
            pdf.cell(cols_w[j], row_height, txt, 1, 0, align)
        pdf.ln()

    # Summary
    pdf.ln(5)
    current_y = pdf.get_y()
    
    pdf.set_xy(15, current_y)
    pdf.set_font(use_f, 'B', 14)
    pdf.cell(0, 7, "หมายเหตุ / Remarks:", 0, 1)
    pdf.set_font(use_f, '', 13)
    pdf.multi_cell(100, 5, remark_text, 0, 'L')
    
    sum_x_label = 135
    sum_x_val = 175
    sum_y = current_y
    
    def print_sum_row(label, value, bold=False, line=False):
        nonlocal sum_y
        pdf.set_xy(sum_x_label, sum_y)
        pdf.set_font(use_f, 'B' if bold else '', 13)
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

    # Signatures
    pdf.set_y(-25) 
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
    st.session_state.grid_df = pd.DataFrame([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0.0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 15)
    reset_keys = ["c_name_in", "contact_in", "c_addr_in", "c_tel_in", "c_fax_in", "remark_in", "s1_in", "s2_in", "s3_in"]
    for k in reset_keys:
        if k in st.session_state: st.session_state[k] = ""
    st.session_state["cust_selector_tab1"] = "-- พิมพ์เอง --"
    st.session_state.generated_pdf_bytes = None
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
                st.text_input("แฟกซ์", key="my_fax_in") # ย้ายแฟกซ์มาตรงนี้ให้สมดุล
                
        with c2:
            st.markdown("""<div style="background-color:#eff6ff; padding:15px; border-radius:10px;">""", unsafe_allow_html=True)
            dc1, dc2 = st.columns(2)
            with dc1:
                st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d')}-001", key="doc_no_in")
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
            # Dropdown เลือกลูกค้า (Logic เดิม)
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
            st.write("") # Spacer
            st.write("") # Spacer
            st.write("") # Spacer (ดันลงมาให้ตรงกับ address)
            st.text_input("เบอร์แฟกซ์", key="c_fax_in")

    # 3. Items Table
    st.markdown("##### 📦 รายการสินค้า (Items)")
    
    prod_opts = st.session_state.db_products['รหัสสินค้า'].astype(str).unique().tolist()
    
    # Logic เดิม 100%
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

    # Auto-fill Logic (คงเดิม)
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

    # Calculation Logic
    calc_df = edited_df.copy()
    calc_df['q'] = calc_df['จำนวน'].apply(to_num)
    calc_df['p'] = calc_df['ราคา'].apply(to_num)
    calc_df['d'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['total'] = (calc_df['q'] * calc_df['p']) - calc_df['d']
    
    sum_gross = (calc_df['q'] * calc_df['p']).sum()
    sum_disc = calc_df['d'].sum()
    sum_sub = calc_df['total'].sum()

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
        vat_val = sum_sub * 0.07 if has_vat else 0.0
        grand_total = sum_sub + vat_val
        
        vat_style = "" if has_vat else "display: none;"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">ยอดรวมทั้งสิ้น (Grand Total)</div>
            <div class="metric-value">{grand_total:,.2f}</div>
            <div style="margin-top: 15px; font-size: 0.9rem; color: #555; text-align: right; border-top: 1px dashed #ccc; padding-top:10px;">
                <table style="width: 100%;">
                    <tr><td style="text-align: left; color:#666;">รวมสินค้า:</td><td style="text-align: right;">{sum_gross:,.2f}</td></tr>
                    <tr><td style="text-align: left; color:#666;">ส่วนลด:</td><td style="text-align: right; color: #dc2626;">-{sum_disc:,.2f}</td></tr>
                    <tr><td style="text-align: left; font-weight: 600;">ก่อนภาษี:</td><td style="text-align: right; font-weight: 600;">{sum_sub:,.2f}</td></tr>
                    <tr style="{vat_style}"><td style="text-align: left; color:#666;">VAT 7%:</td><td style="text-align: right;">{vat_val:,.2f}</td></tr>
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
            # 1. Save History (Logic คงเดิม)
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
            
            # 2. Create PDF (Logic คงเดิม)
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
                st.info("1. ดาวน์โหลดไฟล์ (Download)")
                st.download_button(
                    "📥 ดาวน์โหลด PDF", 
                    st.session_state.generated_pdf_bytes, 
                    f"{st.session_state.last_doc_no}.pdf", 
                    "application/pdf", 
                    use_container_width=True,
                    type="primary"
                )
            
            with act_col2:
                st.info("2. ส่งอีเมลหาลูกค้า (Send Email)")
                with st.form("email_form"):
                    recip_email = st.text_input("อีเมลลูกค้า", placeholder="customer@example.com")
                    email_subj = st.text_input("หัวข้ออีเมล", value=f"ใบเสนอราคาเลขที่ {st.session_state.last_doc_no}")
                    email_body = st.text_area("ข้อความ", value="เรียน ลูกค้า,\n\nแนบใบเสนอราคามาพร้อมกับอีเมลนี้ครับ\n\nขอบคุณครับ")
                    
                    submitted = st.form_submit_button("📤 ส่งอีเมลทันที", use_container_width=True)
                    
                    if submitted:
                        if not email_sender or not email_password:
                            st.error("❌ กรุณากรอกอีเมลและรหัสผ่านผู้ส่งใน Sidebar ด้านซ้ายก่อน")
                        elif not recip_email:
                            st.error("❌ กรุณากรอกอีเมลลูกค้า")
                        else:
                            success, msg = send_email_with_attachment(
                                email_sender, email_password, recip_email, 
                                email_subj, email_body, 
                                st.session_state.generated_pdf_bytes, 
                                f"{st.session_state.last_doc_no}.pdf"
                            )
                            if success:
                                st.success(f"✅ {msg}")
                                if lottie_success:
                                    st_lottie(lottie_success, height=150, key="success_anim")
                            else:
                                st.error(f"❌ {msg}")

# ------------------------------------------------------------------
# TAB 2: ลูกค้า (Logic เดิม 100% ห้ามยุ่ง) -> แค่ใส่ Container ให้ดูดี
# ------------------------------------------------------------------
with tab2:
    with st.container(border=True):
        st.subheader("👥 จัดการฐานข้อมูลลูกค้า")
        st.info("💡 วิธีใช้: แก้ไขข้อมูลในตาราง หรือติ๊ก 'ลบ' แล้วกดปุ่มบันทึกด้านล่าง (ปุ่มเดียวจบ)")
        
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
# TAB 3: สินค้า (Logic เดิม 100% ห้ามยุ่ง) -> แค่ใส่ Container ให้ดูดี
# ------------------------------------------------------------------
with tab3:
    with st.container(border=True):
        st.subheader("📦 จัดการฐานข้อมูลสินค้า")
        st.info("💡 วิธีใช้: แก้ไขข้อมูลในตาราง หรือติ๊ก 'ลบ' แล้วกดปุ่มบันทึกด้านล่าง (ปุ่มเดียวจบ)")
        
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
# TAB 4: ประวัติ (Logic เดิม 100% ห้ามยุ่ง)
# ------------------------------------------------------------------
with tab4:
    with st.container(border=True):
        st.subheader("🗂️ ประวัติใบเสนอราคา")
        
        if not st.session_state.db_history.empty:
            c_hist1, c_hist2 = st.columns([0.7, 0.3])
            with c_hist1:
                sel_hist = st.selectbox("เลือกเอกสารเพื่อแก้ไข", st.session_state.db_history['doc_no'].tolist())
            with c_hist2:
                if st.button("🔄 โหลดข้อมูลกลับหน้าแรก", use_container_width=True):
                    row = st.session_state.db_history[st.session_state.db_history['doc_no'] == sel_hist].iloc[0]
                    data = json.loads(row['data_json'])
                    
                    st.session_state.grid_df = pd.DataFrame.from_dict(data['grid_df'])
                    st.session_state.c_name_in = data.get('c_name', '')
                    st.session_state.contact_in = data.get('contact', '')
                    st.session_state.c_addr_in = data.get('c_addr', '')
                    st.session_state.c_tel_in = data.get('c_tel', '')
                    st.session_state.c_fax_in = data.get('c_fax_in', '') # Added compat
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
