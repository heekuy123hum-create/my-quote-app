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

                # ✅ FIX: กัน index ค้าง
                if 'Unnamed: 0' in temp_df.columns:
                    temp_df = temp_df.drop(columns=['Unnamed: 0'])

                # ✅ FIX: กัน column หาย
                required_cols = ["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร"]
                for col in required_cols:
                    if col not in temp_df.columns:
                        temp_df[col] = ""

                if 'ลบ' not in temp_df.columns:
                    temp_df.insert(0, 'ลบ', False)

                # ลบแฟกซ์
                if 'แฟกซ์' in temp_df.columns:
                    temp_df = temp_df.drop(columns=['แฟกซ์'])

                temp_df = temp_df.fillna("")  # ✅ FIX

                st.session_state.db_customers = temp_df

            except:
                st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร"])
        else:
            st.session_state.db_customers = pd.DataFrame([
                {"ลบ": False, "รหัส": "C001", "ชื่อบริษัท": "ลูกค้าทั่วไป (เงินสด)", "ผู้ติดต่อ": "-", "ที่อยู่": "-", "โทร": "-"}
            ])

        st.session_state.db_customers['ลบ'] = st.session_state.db_customers['ลบ'].fillna(False).astype(bool)

    # --- 2. โหลดข้อมูลสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                temp_df_p = pd.read_csv(PROD_FILE, encoding='utf-8-sig')

                if 'Unnamed: 0' in temp_df_p.columns:
                    temp_df_p = temp_df_p.drop(columns=['Unnamed: 0'])

                # ✅ FIX: กัน column หาย
                required_cols_p = ["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"]
                for col in required_cols_p:
                    if col not in temp_df_p.columns:
                        temp_df_p[col] = ""

                if 'รหัสสินค้า' in temp_df_p.columns:
                    temp_df_p['รหัสสินค้า'] = temp_df_p['รหัสสินค้า'].astype(str)

                if 'ลบ' not in temp_df_p.columns:
                    temp_df_p.insert(0, 'ลบ', False)

                temp_df_p = temp_df_p.fillna("")  # ✅ FIX

                st.session_state.db_products = temp_df_p

            except:
                st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            st.session_state.db_products = pd.DataFrame([
                {"ลบ": False, "รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง", "ราคา": 1000, "หน่วย": "ชิ้น"}
            ])

        st.session_state.db_products['ลบ'] = st.session_state.db_products['ลบ'].fillna(False).astype(bool)

    # --- 3. โหลดประวัติ ---
    if "db_history" not in st.session_state:
        if os.path.exists(HISTORY_FILE):
            try:
                temp_hist = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')

                # ✅ FIX: กัน column หาย
                required_hist_cols = ["ลบ", "timestamp", "doc_no", "customer", "total", "data_json"]
                for col in required_hist_cols:
                    if col not in temp_hist.columns:
                        temp_hist[col] = ""

                if 'Unnamed: 0' in temp_hist.columns:
                    temp_hist = temp_hist.drop(columns=['Unnamed: 0'])

                if 'ลบ' not in temp_hist.columns:
                    temp_hist.insert(0, 'ลบ', False)

                # ✅ FIX: กัน JSON พัง
                temp_hist['data_json'] = temp_hist['data_json'].fillna("").astype(str)

                temp_hist = temp_hist.fillna("")

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

    df_to_save = df_to_save.fillna("")  # ✅ FIX

    df_to_save = df_to_save.reset_index(drop=True)

    df_to_save.to_csv(filename, index=False, encoding='utf-8-sig')
    return df_to_save

def to_int(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return int(round(float(val))) if val is not None else 0
    except:
        return 0

def generate_doc_no(prefix_type="QT"):
    today_str = datetime.now().strftime('%Y%m%d')
    prefix = f"{prefix_type}-{today_str}"
    
    if st.session_state.db_history.empty:
        return f"{prefix}-001"
    
    hist_df = st.session_state.db_history.copy()
    hist_df['doc_no'] = hist_df['doc_no'].astype(str)
    
    matched_docs = hist_df[hist_df['doc_no'].str.startswith(prefix, na=False)]
    
    if matched_docs.empty:
        return f"{prefix}-001"
    
    max_run = 0
    for doc in matched_docs['doc_no']:
        try:
            parts = doc.split('-')
            if len(parts) >= 3:
                run_num = int(parts[-1])
                if run_num > max_run:
                    max_run = run_num
        except:
            pass
            
    return f"{prefix}-{max_run + 1:03d}"
