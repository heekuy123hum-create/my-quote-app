import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import json
import requests
from streamlit_lottie import st_lottie
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from bahttext import bahttext 
import base64

# ==========================================
# นำเข้าโมดูลจากไฟล์ที่แยกออกไป (เดี๋ยวเราจะสร้าง 2 ไฟล์นี้ทีหลัง)
# ==========================================
from database import load_data, save_data, generate_doc_no, to_int, CUST_FILE, PROD_FILE, HISTORY_FILE
from pdf_generator import create_pdf, convert_pdf_to_image

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

# เริ่มต้นตัวแปร Session State
if "grid_df" not in st.session_state:
    st.session_state.grid_df = pd.DataFrame(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 15
    )
if "generated_pdf_bytes" not in st.session_state:
    st.session_state.generated_pdf_bytes = None
if "last_doc_no" not in st.session_state:
    st.session_state.last_doc_no = ""
if "convert_pdf_bytes" not in st.session_state:
    st.session_state.convert_pdf_bytes = None
if "convert_filename" not in st.session_state:
    st.session_state.convert_filename = ""

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

# เรียกใช้งานการโหลดฐานข้อมูล
load_data()

# ==========================================
# 3. USER INTERFACE
# ==========================================

# --- ฟังก์ชันช่วยเหลือสำหรับแสดง PDF ---
def display_pdf(pdf_bytes):
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def clear_all_data():
    st.session_state.grid_df = pd.DataFrame([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 15)
    reset_keys = ["c_name_in", "contact_in", "c_addr_in", "c_tel_in", "c_fax_in", "remark_in", "s1_in", "s2_in", "s3_in", "img1_in", "img2_in", "img3_in"]
    for k in reset_keys:
        if k in st.session_state: st.session_state[k] = ""
    st.session_state["cust_selector_tab1"] = "-- พิมพ์เอง --"
    st.session_state.generated_pdf_bytes = None
    # Reset Doc No to new auto increment (Quotation by default)
    st.session_state.doc_no_in = generate_doc_no("QT") 
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
# TAB 1: Quotation
# ------------------------------------------------------------------
with tab1:
    # 1. Header Info Section (Seller + Doc Info)
    with st.expander("🧾 ข้อมูลเอกสารและผู้ขาย (Document Info)", expanded=True):
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
                # ใช้ Function generate_doc_no("QT") เป็นค่า default
                st.text_input("เลขที่ใบเสนอราคา", value=generate_doc_no("QT"), key="doc_no_in")
                st.text_input("ยืนราคา (วัน)", "30", key="valid_days_in")
            with dc2:
                st.date_input("วันที่เอกสาร", date.today(), key="doc_date_in")
                st.text_input("เครดิต (วัน)", "30", key="credit_in")
            
            st.text_input("กำหนดส่งสินค้า", "ภายใน 7-15 วัน", key="due_date_in")
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. Customer Info Section
    with st.expander("👤 ข้อมูลลูกค้า (Customer Details)", expanded=True):
        # Header Row for Customer
        cust_h1, cust_h2 = st.columns([0.6, 0.4])
        with cust_h1: 
            pass # Removed Markdown Header to avoid duplication with Expander title
        with cust_h2: 
            # Dropdown เลือกลูกค้า
            cust_list = []
            if not st.session_state.db_customers.empty:
                cust_list = st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist()
            
            opts = ["-- พิมพ์เอง --"] + cust_list
                
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
    with st.expander("📦 รายการสินค้า (Items)", expanded=True):
        
        prod_opts = st.session_state.db_products['รหัสสินค้า'].astype(str).unique().tolist()
        
        edited_df = st.data_editor(
            st.session_state.grid_df,
            column_config={
                "รหัสสินค้า": st.column_config.SelectboxColumn("รหัส", options=prod_opts, width="medium"),
                "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
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
                    edited_df.at[idx, 'ราคา'] = int(info['ราคา'])
                    needs_rerun = True
        
        if needs_rerun:
            st.session_state.grid_df = edited_df
            st.rerun()
        else:
            st.session_state.grid_df = edited_df

    # Calculation Logic
    calc_df = edited_df.copy()
    calc_df['q'] = calc_df['จำนวน'].apply(to_int)
    calc_df['p'] = calc_df['ราคา'].apply(to_int)
    calc_df['d'] = calc_df['ส่วนลด'].apply(to_int)
    calc_df['total'] = calc_df.apply(lambda x: int(round((x['q'] * x['p']) - x['d'])), axis=1)
    
    sum_gross = int((calc_df['q'] * calc_df['p']).sum())
    sum_disc = int(calc_df['d'].sum())
    sum_sub = int(calc_df['total'].sum())

    # 4. Summary & Actions
    with st.expander("📊 สรุปยอดและบันทึกเอกสาร", expanded=True):
        f_col1, f_col2 = st.columns([1.8, 1])
        
        with f_col1:
            st.markdown("##### 📝 หมายเหตุ & การอนุมัติ")
            st.text_area("หมายเหตุ (Remarks)", value="1. ราคายังไม่รวม VAT 7%\n2. กำหนดยืนราคา 30 วัน", key="remark_in", height=100, label_visibility="collapsed")
            
            st.markdown("<br>", unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            with s1:
                st.text_input("ผู้สั่งซื้อ", key="s1_in")
                st.file_uploader("ลายเซ็น", type=["png", "jpg", "jpeg"], key="img1_in", label_visibility="collapsed")
            with s2:
                st.text_input("พนักงานขาย", key="s2_in")
                st.file_uploader("ลายเซ็น", type=["png", "jpg", "jpeg"], key="img2_in", label_visibility="collapsed")
            with s3:
                st.text_input("ผู้อนุมัติ", key="s3_in")
                st.file_uploader("ลายเซ็น", type=["png", "jpg", "jpeg"], key="img3_in", label_visibility="collapsed")

        with f_col2:
            # Grand Total Card
            has_vat = st.checkbox("คำนวณ VAT 7%", value=True)
            vat_val = int(round(sum_sub * 0.07)) if has_vat else 0
            grand_total = sum_sub + vat_val
            
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
                    "has_vat": has_vat,
                    "my_comp": st.session_state.my_comp_in, "my_addr": st.session_state.my_addr_in,
                    "my_tel": st.session_state.my_tel_in, "my_fax": st.session_state.my_fax_in, "my_tax": st.session_state.my_tax_in
                }
                
                new_rec = {
                    "ลบ": False,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "doc_no": doc_no,
                    "customer": st.session_state.c_name_in,
                    "total": grand_total,
                    "data_json": json.dumps(json_data, ensure_ascii=False)
                }
                
                # ตรวจสอบว่าถ้าเป็นการแก้ไขเอกสารเดิม ให้เขียนทับแทนการเพิ่มบรรทัดใหม่
                if not st.session_state.db_history.empty and doc_no in st.session_state.db_history['doc_no'].values:
                    st.session_state.db_history = st.session_state.db_history[st.session_state.db_history['doc_no'] != doc_no]
                
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
                
                # รวบรวมข้อมูลลายเซ็นเพื่อส่งให้ pdf_generator
                sigs = {
                    's1': st.session_state.s1_in,
                    's2': st.session_state.s2_in,
                    's3': st.session_state.s3_in,
                    'img1': st.session_state.get('img1_in'),
                    'img2': st.session_state.get('img2_in'),
                    'img3': st.session_state.get('img3_in')
                }
                
                pdf_bytes = create_pdf(
                    pdf_data, calc_df, 
                    {"gross": sum_gross, "discount": sum_disc, "subtotal": sum_sub, "vat": vat_val, "grand_total": grand_total},
                    sigs,
                    st.session_state.remark_in, has_vat,
                    doc_title="ใบเสนอราคา (QUOTATION)"
                )
                
                st.session_state.generated_pdf_bytes = pdf_bytes
                if lottie_success:
                    st_lottie(lottie_success, height=150, key="success_anim")
                st.success(f"บันทึกเอกสาร {doc_no} เรียบร้อย!")

        if st.session_state.generated_pdf_bytes:
            st.markdown("##### 📄 ตัวอย่างเอกสาร (Preview)")
            display_pdf(st.session_state.generated_pdf_bytes)
            
            st.markdown("##### 📥 ดาวน์โหลดเอกสาร")
            export_format = st.radio("เลือกนามสกุลไฟล์ที่ต้องการดาวน์โหลด:", ["PDF", "JPG", "PNG"], horizontal=True, key="export_format_tab1")
            
            if export_format == "PDF":
                st.download_button(
                    label="📄 ดาวน์โหลด PDF",
                    data=st.session_state.generated_pdf_bytes,
                    file_name=f"Quotation_{st.session_state.doc_no_in}.pdf",
                    mime="application/pdf",
                    type="secondary"
                )
            else:
                img_bytes, err = convert_pdf_to_image(st.session_state.generated_pdf_bytes, export_format)
                if img_bytes:
                    st.download_button(
                        label=f"🖼️ ดาวน์โหลด {export_format}",
                        data=img_bytes,
                        file_name=f"Quotation_{st.session_state.doc_no_in}.{export_format.lower()}",
                        mime=f"image/{export_format.lower()}",
                        type="secondary"
                    )
                else:
                    st.error(f"ไม่สามารถแปลงไฟล์ได้: {err}")
            
            # Email Form
            with st.expander("📧 ส่งอีเมลหาลูกค้าทันที"):
                em_receiver = st.text_input("อีเมลลูกค้า", placeholder="client@example.com")
                em_subject = st.text_input("หัวข้อ", value=f"ใบเสนอราคา {st.session_state.doc_no_in}")
                em_body = st.text_area("ข้อความ", value="เรียน ลูกค้า,\n\nแนบมาพร้อมกับใบเสนอราคา\n\nขอบคุณครับ")
                if st.button("ส่งอีเมล"):
                    if email_sender and email_password and em_receiver:
                        success, msg = send_email_with_attachment(email_sender, email_password, em_receiver, em_subject, em_body, st.session_state.generated_pdf_bytes, f"QT_{st.session_state.doc_no_in}.pdf")
                        if success: st.success(msg)
                        else: st.error(msg)
                    else:
                        st.error("กรุณากรอกข้อมูลอีเมลผู้ส่งในเมนูซ้ายมือให้ครบถ้วน")

# ------------------------------------------------------------------
# TAB 2: Customer Database
# ------------------------------------------------------------------
with tab2:
    st.header("👥 ฐานข้อมูลลูกค้า")
    st.info("💡 วิธีใช้: กรอกข้อมูลในบรรทัดใหม่ได้เลย ข้อมูลจะบันทึกเมื่อกดปุ่ม 'บันทึก' หากต้องการลบ ให้ติ๊กช่อง 'ลบ' แล้วกดบันทึก")

    cust_df = st.session_state.db_customers.copy()
    
    cols = list(cust_df.columns)
    if 'ลบ' in cols:
        cols.insert(0, cols.pop(cols.index('ลบ')))
        cust_df = cust_df[cols]

    edited_cust = st.data_editor(
        cust_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "ลบ": st.column_config.CheckboxColumn("ลบ (ติ๊กเพื่อลบข้อมูล)", default=False, width="small"),
            "รหัส": st.column_config.TextColumn("รหัสลูกค้า", width="small"),
            "ชื่อบริษัท": st.column_config.TextColumn("ชื่อบริษัท", width="large"),
            "ที่อยู่": st.column_config.TextColumn("ที่อยู่", width="large"),
        },
        key="editor_cust"
    )
    
    if st.button("💾 บันทึกข้อมูลลูกค้า", type="primary"):
        to_save = edited_cust[edited_cust['ลบ'] == False].copy()
        to_save = save_data(to_save, CUST_FILE, key_col="ชื่อบริษัท")
        st.session_state.db_customers = to_save
        st.success("บันทึกข้อมูลลูกค้าเรียบร้อย! (รายการที่ติ๊กลบถูกลบออกแล้ว)")
        st.rerun()

# ------------------------------------------------------------------
# TAB 3: Product Database
# ------------------------------------------------------------------
with tab3:
    st.header("📦 ฐานข้อมูลสินค้า")
    st.info("💡 วิธีใช้: กรอกข้อมูลในบรรทัดใหม่ได้เลย ข้อมูลจะบันทึกเมื่อกดปุ่ม 'บันทึก' หากต้องการลบ ให้ติ๊กช่อง 'ลบ' แล้วกดบันทึก")

    prod_df = st.session_state.db_products.copy()
    
    cols_p = list(prod_df.columns)
    if 'ลบ' in cols_p:
        cols_p.insert(0, cols_p.pop(cols_p.index('ลบ')))
        prod_df = prod_df[cols_p]

    edited_prod = st.data_editor(
        prod_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "ลบ": st.column_config.CheckboxColumn("ลบ (ติ๊กเพื่อลบข้อมูล)", default=False, width="small"),
            "รหัสสินค้า": st.column_config.TextColumn("รหัส", width="small"),
            "รายการ": st.column_config.TextColumn("ชื่อสินค้า", width="large"),
            "ราคา": st.column_config.NumberColumn("ราคา", format="%.0f"),
        },
        key="editor_prod"
    )
    
    if st.button("💾 บันทึกข้อมูลสินค้า", type="primary"):
        to_save_p = edited_prod[edited_prod['ลบ'] == False].copy()
        to_save_p = save_data(to_save_p, PROD_FILE, key_col="รายการ")
        st.session_state.db_products = to_save_p
        st.success("บันทึกข้อมูลสินค้าเรียบร้อย! (รายการที่ติ๊กลบถูกลบออกแล้ว)")
        st.rerun()

# ------------------------------------------------------------------
# TAB 4: History & Convert
# ------------------------------------------------------------------
with tab4:
    st.header("🗂️ ประวัติใบเสนอราคา & แปลงเอกสาร")
    
    if not st.session_state.db_history.empty:
        # Separate View
        col_hist1, col_hist2 = st.columns([0.65, 0.35])
        
        with col_hist1:
            st.subheader("รายการเอกสารทั้งหมด")
            st.write("💡 ติ๊กช่อง 'ลบ' แล้วกดปุ่มบันทึกด้านล่างเพื่อลบเอกสาร")
            
            disp_hist = st.session_state.db_history.copy()
            
            # นำคอลัมน์ 'ลบ' มาไว้หน้าสุด
            cols_h = list(disp_hist.columns)
            if 'ลบ' in cols_h:
                cols_h.insert(0, cols_h.pop(cols_h.index('ลบ')))
                disp_hist = disp_hist[cols_h]
            
            # ซ่อนคอลัมน์ data_json สำหรับการแสดงผล
            if 'data_json' in disp_hist.columns:
                disp_hist = disp_hist.drop(columns=['data_json'])
                
            edited_hist = st.data_editor(
                disp_hist,
                use_container_width=True,
                height=500,
                hide_index=True,
                column_config={
                    "ลบ": st.column_config.CheckboxColumn("ลบ (ติ๊กเพื่อลบ)", default=False, width="small"),
                },
                key="editor_hist"
            )
            
            if st.button("🗑️ บันทึกการลบเอกสาร", type="primary", use_container_width=True):
                st.session_state.db_history['ลบ'] = edited_hist['ลบ'].values
                to_save_h = st.session_state.db_history[st.session_state.db_history['ลบ'] == False].copy()
                to_save_h = save_data(to_save_h, HISTORY_FILE, key_col="doc_no")
                st.session_state.db_history = to_save_h
                st.success("ลบเอกสารที่เลือกเรียบร้อย!")
                st.rerun()
                
        with col_hist2:
            st.markdown("""<div class="custom-card">""", unsafe_allow_html=True)
            st.subheader("🔄 แปลงเอกสาร (Convert)")
            st.write("เลือกใบเสนอราคา (QT) เพื่อแปลงเป็นใบแจ้งหนี้ (IV) หรือใบเสร็จ (RE)")
            
            # Filter only Quotations
            qt_list = st.session_state.db_history[
                st.session_state.db_history['doc_no'].astype(str).str.startswith("QT")
            ]['doc_no'].tolist()
            
            if not qt_list:
                st.warning("ยังไม่มีใบเสนอราคาในระบบ")
            else:
                selected_qt = st.selectbox("เลือกใบเสนอราคาที่ต้องการแปลง", qt_list)
                convert_date = st.date_input("วันที่เอกสารใหม่", date.today())
                
                # Fetch Data
                if selected_qt:
                    row_data = st.session_state.db_history[st.session_state.db_history['doc_no'] == selected_qt].iloc[0]
                    json_raw = row_data['data_json']
                    
                    try:
                        data = json.loads(json_raw)
                        
                        st.divider()
                        st.markdown(f"**ลูกค้า:** {data.get('c_name', '-')}")
                        st.markdown(f"**ยอดรวม:** {row_data['total']:,.0f} บาท")
                        
                        c_btn1, c_btn2 = st.columns(2)
                        
                        action_type = None
                        
                        with c_btn1:
                            if st.button("📄 สร้างใบแจ้งหนี้\n(Invoice)", use_container_width=True):
                                action_type = "IV"
                        with c_btn2:
                            if st.button("🧾 สร้างใบเสร็จ\n(Receipt)", use_container_width=True):
                                action_type = "RE"
                                
                        if action_type:
                            # 1. Generate New Doc No
                            new_doc_no = generate_doc_no(action_type)
                            
                            # 2. Reconstruct DataFrame
                            items_df = pd.DataFrame.from_dict(data['grid_df'])
                            
                            # Recalculate totals
                            items_df['q'] = items_df['จำนวน'].apply(to_int)
                            items_df['p'] = items_df['ราคา'].apply(to_int)
                            items_df['d'] = items_df['ส่วนลด'].apply(to_int)
                            items_df['total'] = items_df.apply(lambda x: int(round((x['q'] * x['p']) - x['d'])), axis=1)
                            
                            s_gross = int((items_df['q'] * items_df['p']).sum())
                            s_disc = int(items_df['d'].sum())
                            s_sub = int(items_df['total'].sum())
                            has_vat = data.get('has_vat', True)
                            v_val = int(round(s_sub * 0.07)) if has_vat else 0
                            g_total = s_sub + v_val
                            
                            # 3. Prepare PDF Data
                            pdf_info = {
                                "my_comp": data.get('my_comp', st.session_state.my_comp_in or "บริษัท ศิวกิจ เทรดดิ้ง จำกัด"), 
                                "my_addr": data.get('my_addr', st.session_state.my_addr_in or ""),
                                "my_tel": data.get('my_tel', st.session_state.my_tel_in or ""), 
                                "my_fax": data.get('my_fax', st.session_state.my_fax_in or ""), 
                                "my_tax": data.get('my_tax', st.session_state.my_tax_in or ""),
                                "doc_no": new_doc_no, 
                                "doc_date": convert_date.strftime("%d/%m/%Y"),
                                "due_date": data.get('due_date', ""),
                                "valid_days": data.get('valid_days', "30"),
                                "credit": data.get('credit', "30"),
                                "exp_date": (convert_date + timedelta(days=30)).strftime("%d/%m/%Y"),
                                "c_name": data.get('c_name', ""), "contact": data.get('contact', ""),
                                "c_addr": data.get('c_addr', ""), "c_tel": data.get('c_tel', ""), "c_fax": data.get('c_fax', "")
                            }
                            
                            # Titles
                            titles = {
                                "IV": "ใบแจ้งหนี้ / ใบวางบิล (INVOICE / BILLING NOTE)",
                                "RE": "ใบเสร็จรับเงิน (RECEIPT)"
                            }
                            
                            pdf_bytes = create_pdf(
                                pdf_info, items_df, 
                                {"gross": s_gross, "discount": s_disc, "subtotal": s_sub, "vat": v_val, "grand_total": g_total},
                                {"s1": data.get('s1', ""), "s2": data.get('s2', ""), "s3": data.get('s3', "")},
                                data.get('remark', ""), has_vat,
                                doc_title=titles[action_type]
                            )
                            
                            # 4. Save to History
                            # Reuse json data but update doc info
                            data['doc_no'] = new_doc_no
                            data['doc_date_str'] = str(convert_date)
                            
                            new_rec = {
                                "ลบ": False,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "doc_no": new_doc_no,
                                "customer": data.get('c_name'),
                                "total": g_total,
                                "data_json": json.dumps(data, ensure_ascii=False)
                            }
                            
                            st.session_state.db_history = pd.concat([pd.DataFrame([new_rec]), st.session_state.db_history], ignore_index=True)
                            save_data(st.session_state.db_history, HISTORY_FILE)
                            
                            st.session_state.convert_pdf_bytes = pdf_bytes
                            st.session_state.convert_filename = f"{action_type}_{new_doc_no}.pdf"
                            st.success(f"สร้างเอกสาร {new_doc_no} สำเร็จ!")
                            st.rerun()

                    except Exception as e:
                        st.error(f"Error parsing data: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

            # --- NEW EDIT SECTION ---
            st.markdown("""<div class="custom-card">""", unsafe_allow_html=True)
            st.subheader("✏️ ดึงข้อมูลไปแก้ไข (Load to Edit)")
            st.write("เลือกเอกสารเพื่อนำข้อมูลกลับไปแก้ไขที่หน้า 'สร้างใบเสนอราคา'")
            
            all_docs_list = st.session_state.db_history['doc_no'].tolist()
            if not all_docs_list:
                st.warning("ไม่มีเอกสารในระบบ")
            else:
                selected_edit = st.selectbox("เลือกเอกสารที่ต้องการแก้ไข", all_docs_list, key="edit_doc_selector")
                if st.button("ดึงข้อมูลไปแก้ไข 📝", use_container_width=True):
                    row_data = st.session_state.db_history[st.session_state.db_history['doc_no'] == selected_edit].iloc[0]
                    json_raw = row_data['data_json']
                    try:
                        data = json.loads(json_raw)
                        
                        # อัปเดต session_state ของหน้า Tab 1
                        st.session_state.doc_no_in = selected_edit
                        if 'my_comp' in data: st.session_state.my_comp_in = data['my_comp']
                        if 'my_addr' in data: st.session_state.my_addr_in = data['my_addr']
                        if 'my_tel' in data: st.session_state.my_tel_in = data['my_tel']
                        if 'my_tax' in data: st.session_state.my_tax_in = data['my_tax']
                        if 'my_fax' in data: st.session_state.my_fax_in = data['my_fax']
                        if 'valid_days' in data: st.session_state.valid_days_in = data['valid_days']
                        
                        try:
                            if 'doc_date_str' in data:
                                st.session_state.doc_date_in = datetime.strptime(data['doc_date_str'], '%Y-%m-%d').date()
                        except:
                            st.session_state.doc_date_in = date.today()
                            
                        if 'credit' in data: st.session_state.credit_in = data['credit']
                        if 'due_date' in data: st.session_state.due_date_in = data['due_date']
                        if 'c_name' in data: st.session_state.c_name_in = data['c_name']
                        if 'c_addr' in data: st.session_state.c_addr_in = data['c_addr']
                        if 'contact' in data: st.session_state.contact_in = data['contact']
                        if 'c_tel' in data: st.session_state.c_tel_in = data['c_tel']
                        if 'c_fax' in data: st.session_state.c_fax_in = data['c_fax']
                        if 'remark' in data: st.session_state.remark_in = data['remark']
                        if 's1' in data: st.session_state.s1_in = data['s1']
                        if 's2' in data: st.session_state.s2_in = data['s2']
                        if 's3' in data: st.session_state.s3_in = data['s3']
                        
                        if 'grid_df' in data:
                            loaded_df = pd.DataFrame.from_dict(data['grid_df'])
                            # ให้แน่ใจว่าจำนวนแถวครบ 15 แถวเพื่อความสวยงามในหน้า UI
                            while len(loaded_df) < 15:
                                loaded_df = pd.concat([loaded_df, pd.DataFrame([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}])], ignore_index=True)
                            st.session_state.grid_df = loaded_df
                            
                        st.success(f"ดึงข้อมูล {selected_edit} สำเร็จ! กรุณาไปที่แท็บ 'สร้างใบเสนอราคา' เพื่อแก้ไข")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {str(e)}")
            st.markdown("</div>", unsafe_allow_html=True)

            # Download Section
            if st.session_state.convert_pdf_bytes:
                st.markdown("##### 📄 ตัวอย่างเอกสาร (Preview)")
                display_pdf(st.session_state.convert_pdf_bytes)
                
                st.markdown("##### 📥 ดาวน์โหลดเอกสารล่าสุด")
                export_format_t4 = st.radio("เลือกนามสกุลไฟล์ที่ต้องการดาวน์โหลด:", ["PDF", "JPG", "PNG"], horizontal=True, key="export_format_tab4")
                
                doc_base_name = st.session_state.get('convert_filename', 'document.pdf').replace('.pdf', '')
                
                if export_format_t4 == "PDF":
                    st.download_button(
                        label=f"ดาวน์โหลด {doc_base_name}.pdf",
                        data=st.session_state.convert_pdf_bytes,
                        file_name=f"{doc_base_name}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    img_bytes, err = convert_pdf_to_image(st.session_state.convert_pdf_bytes, export_format_t4)
                    if img_bytes:
                        st.download_button(
                            label=f"ดาวน์โหลด {doc_base_name}.{export_format_t4.lower()}",
                            data=img_bytes,
                            file_name=f"{doc_base_name}.{export_format_t4.lower()}",
                            mime=f"image/{export_format_t4.lower()}",
                            type="primary",
                            use_container_width=True
                        )
                    else:
                        st.error(f"ไม่สามารถแปลงไฟล์ได้: {err}")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
    else:
        st.info("ยังไม่มีประวัติเอกสาร")
