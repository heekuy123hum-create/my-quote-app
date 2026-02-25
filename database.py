import pandas as pd
import os
import streamlit as st
from datetime import datetime

# ชื่อไฟล์สำหรับเก็บข้อมูล
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"
HISTORY_FILE = "history_quotes.csv"

def load_data():
    # --- 1. โหลดข้อมูลลูกค้า ---
    if "db_customers" not in st.session_state:
        if os.path.exists(CUST_FILE):
            try:
                temp_df = pd.read_csv(CUST_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df.columns: temp_df = temp_df.drop(columns=['Unnamed: 0'])
                # ตรวจสอบคอลัมน์ "ลบ" ถ้าไม่มีให้เพิ่ม
                if 'ลบ' not in temp_df.columns:
                    temp_df.insert(0, 'ลบ', False)
                st.session_state.db_customers = temp_df
            except:
                st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            st.session_state.db_customers = pd.DataFrame([
                {"ลบ": False, "รหัส": "C001", "ชื่อบริษัท": "ลูกค้าทั่วไป (เงินสด)", "ผู้ติดต่อ": "-", "ที่อยู่": "-", "โทร": "-", "แฟกซ์": "-"}
            ])
        
        # Ensure boolean type for checkbox
        st.session_state.db_customers['ลบ'] = st.session_state.db_customers['ลบ'].fillna(False).astype(bool)

    # --- 2. โหลดข้อมูลสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                temp_df_p = pd.read_csv(PROD_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df_p.columns: temp_df_p = temp_df_p.drop(columns=['Unnamed: 0'])
                if 'รหัสสินค้า' in temp_df_p.columns:
                    temp_df_p['รหัสสินค้า'] = temp_df_p['รหัสสินค้า'].astype(str)
                # ตรวจสอบคอลัมน์ "ลบ" ถ้าไม่มีให้เพิ่ม
                if 'ลบ' not in temp_df_p.columns:
                    temp_df_p.insert(0, 'ลบ', False)
                st.session_state.db_products = temp_df_p
            except:
                st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            st.session_state.db_products = pd.DataFrame([
                {"ลบ": False, "รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง", "ราคา": 1000, "หน่วย": "ชิ้น"}
            ])
        
        # Ensure boolean type for checkbox
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
    
    # Logic: กรองเฉพาะแถวที่ไม่ได้ติ๊ก "ลบ" และข้อมูลไม่ว่างเปล่า
    if 'ลบ' in df_to_save.columns:
        df_to_save = df_to_save[df_to_save['ลบ'] == False]
        # รีเซ็ตค่าลบเป็น False เผื่อไว้ (แต่จริงๆ ถูกกรองออกไปแล้ว)
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

# --- Function Auto-Increment Doc No (Updated for QT/IV/RE) ---
def generate_doc_no(prefix_type="QT"):
    # prefix_type: QT=Quotation, IV=Invoice, RE=Receipt
    today_str = datetime.now().strftime('%Y%m%d')
    prefix = f"{prefix_type}-{today_str}"
    
    # ถ้าไม่มีประวัติเลย ให้เริ่มที่ 001
    if st.session_state.db_history.empty:
        return f"{prefix}-001"
    
    # ค้นหาเอกสารที่มี Prefix เดียวกันในประวัติ
    hist_df = st.session_state.db_history.copy()
    hist_df['doc_no'] = hist_df['doc_no'].astype(str)
    
    # กรองเฉพาะที่ขึ้นต้นด้วย Prefix ประเภทนี้ (เช่น QT-, IV-)
    # ใช้ startswith เพื่อความแม่นยำ
    matched_docs = hist_df[hist_df['doc_no'].str.startswith(prefix, na=False)]
    
    if matched_docs.empty:
        return f"{prefix}-001"
    
    # หาเลขรันสูงสุดแล้วบวก 1
    max_run = 0
    for doc in matched_docs['doc_no']:
        try:
            # format: PREFIX-YYYYMMDD-XXX
            parts = doc.split('-')
            if len(parts) >= 3:
                run_num = int(parts[-1])
                if run_num > max_run:
                    max_run = run_num
        except:
            pass
            
    return f"{prefix}-{max_run + 1:03d}"