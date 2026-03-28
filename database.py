import pandas as pd
import os
import streamlit as st
from datetime import datetime
from supabase import create_client, Client
import json

# ==========================================
# 1. ตั้งค่าการเชื่อมต่อ Supabase
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    st.error("⚠️ ไม่พบการตั้งค่า SUPABASE_URL หรือ SUPABASE_KEY ระบบอาจทำงานไม่สมบูรณ์")

CUST_FILE = "customers"
PROD_FILE = "products"
HISTORY_FILE = "history_quotes"

# ==========================================
# 2. ฟังก์ชันโหลดข้อมูล
# ==========================================
def load_data():
    if "db_customers" not in st.session_state:
        try:
            response = supabase.table(CUST_FILE).select("*").order("id").execute()
            temp_df = pd.DataFrame(response.data)
            
            required_cols = ["id", "ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร"]
            if temp_df.empty:
                temp_df = pd.DataFrame(columns=required_cols)
            else:
                for col in required_cols:
                    if col not in temp_df.columns:
                        temp_df[col] = ""
                        
            temp_df = temp_df.fillna("")
            st.session_state.db_customers = temp_df
        except Exception as e:
            st.error(f"โหลดข้อมูลลูกค้าไม่สำเร็จ: {e}")
            st.session_state.db_customers = pd.DataFrame(columns=["ลบ", "รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร"])

    if "db_products" not in st.session_state:
        try:
            response = supabase.table(PROD_FILE).select("*").order("id").execute()
            temp_df = pd.DataFrame(response.data)
            
            required_cols = ["id", "ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"]
            if temp_df.empty:
                temp_df = pd.DataFrame(columns=required_cols)
            else:
                for col in required_cols:
                    if col not in temp_df.columns:
                        temp_df[col] = ""
            
            temp_df = temp_df.fillna("")
            st.session_state.db_products = temp_df
        except Exception as e:
            st.error(f"โหลดข้อมูลสินค้าไม่สำเร็จ: {e}")
            st.session_state.db_products = pd.DataFrame(columns=["ลบ", "รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])

    if "db_history" not in st.session_state:
        try:
            response = supabase.table(HISTORY_FILE).select("*").order("id").execute()
            temp_df = pd.DataFrame(response.data)
            
            required_cols = ["id", "ลบ", "date", "doc_no", "c_name", "total", "data_json"]
            if temp_df.empty:
                temp_df = pd.DataFrame(columns=required_cols)
            else:
                for col in required_cols:
                    if col not in temp_df.columns:
                        temp_df[col] = ""
                        
            if not temp_df.empty and 'data_json' in temp_df.columns:
                temp_df['data_json'] = temp_df['data_json'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
                
            temp_df = temp_df.fillna("")
            st.session_state.db_history = temp_df
        except Exception as e:
            st.error(f"โหลดข้อมูลประวัติเอกสารไม่สำเร็จ: {e}")
            st.session_state.db_history = pd.DataFrame(columns=["ลบ", "date", "doc_no", "c_name", "total", "data_json"])

# ==========================================
# 3. ฟังก์ชันบันทึกข้อมูล
# ==========================================
def save_data(df_to_save, table_name, key_col=None):
    df = df_to_save.copy()
    
    if 'ลบ' not in df.columns:
        df['ลบ'] = False

    if key_col and key_col in df.columns:
        df = df[df[key_col].astype(str).str.strip() != ""]

    df = df.fillna("")
    records = df.to_dict(orient='records')
    
    clean_records = []
    for r in records:
        # ✅ FIX: จัดการค่า id ป้องกัน Error 1.0 (invalid input syntax for type integer)
        if 'id' in r:
            if pd.isna(r['id']) or r['id'] == "":
                del r['id']
            else:
                try:
                    # บังคับแปลง 1.0 ให้กลายเป็น 1 ทันที
                    r['id'] = int(float(r['id']))
                except:
                    del r['id']
            
        if table_name == HISTORY_FILE and 'data_json' in r:
            if isinstance(r['data_json'], str):
                try:
                    r['data_json'] = json.loads(r['data_json'])
                except:
                    pass
                    
        clean_records.append(r)

    if len(clean_records) > 0:
        try:
            supabase.table(table_name).upsert(clean_records).execute()
            
            response = supabase.table(table_name).select("*").order("id").execute()
            latest_df = pd.DataFrame(response.data)
            
            if table_name == HISTORY_FILE and 'data_json' in latest_df.columns:
                 latest_df['data_json'] = latest_df['data_json'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
                 
            latest_df = latest_df.fillna("")
            return latest_df
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูลตาราง {table_name}: {e}")
            return df
    return df

# ==========================================
# 4. ฟังก์ชันช่วยเหลืออื่นๆ
# ==========================================
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
    
    today_docs = hist_df[hist_df['doc_no'].str.startswith(prefix, na=False)]
    
    if today_docs.empty:
        return f"{prefix}-001"
    else:
        def extract_run_no(doc_str):
            try:
                return int(doc_str.split("-")[-1])
            except:
                return 0
                
        today_docs['run_no'] = today_docs['doc_no'].apply(extract_run_no)
        max_run = today_docs['run_no'].max()
        next_run = max_run + 1
        return f"{prefix}-{next_run:03d}"
