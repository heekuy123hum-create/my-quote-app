import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os

# --- 1. การตั้งค่าหน้าตาแอป (UI CONFIG) ---
st.set_page_config(page_title="ระบบใบเสนอราคา Pro (Cloud)", layout="wide")

# ดึงค่า Config จาก Render (Environment Variables)
MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# ตรวจสอบการเชื่อมต่อ
if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("❌ มึงยังไม่ได้ตั้งค่า SUPABASE_URL หรือ KEY ในหน้า Environment ของ Render นะ!")
    st.stop()

# เชื่อมต่อฐานข้อมูล
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=MY_SUPABASE_URL,
        key=MY_SUPABASE_KEY
    )
except Exception as e:
    st.error(f"❌ เชื่อมต่อ Supabase ไม่ได้: {e}")
    st.stop()

# --- 2. ฟังก์ชันจัดการข้อมูล (DATABASE LOGIC) ---
def fetch_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- 3. หน้าจอหลัก (MAIN UI) ---
st.title("📄 ระบบออกใบเสนอราคา (Full Version)")

tab_doc, tab_cust, tab_prod = st.tabs(["📝 ออกใบเสนอราคา", "👥 จัดการลูกค้า", "📦 จัดการสินค้า"])

# --- TAB: ออกใบเสนอราคา ---
with tab_doc:
    df_customers = fetch_data("customers")
    df_products = fetch_data("products")

    # ส่วนหัวเอกสาร
    with st.container():
        col_header1, col_header2, col_header3 = st.columns([1.5, 2, 1.5])
        
        with col_header1:
            st.subheader("ข้อมูลลูกค้า")
            # แก้ไขจุดนี้: ป้องกัน Error ถ้าตารางว่าง
            c_options = ["-- เลือกรหัสลูกค้า --"]
            if not df_customers.empty and 'id' in df_customers.columns:
                c_options += df_customers['id'].tolist()
            
            selected_cust_id = st.selectbox("รหัสลูกค้า (ID)", options=c_options)
            
            # --- จุดที่เคย Error (บรรทัด 54) แก้ไขให้ปลอดภัยแล้ว ---
            c_info = {}
            if selected_cust_id != "-- เลือกรหัสลูกค้า --" and not df_customers.empty:
                filtered_cust = df_customers[df_customers['id'] == selected_cust_id]
                if not filtered_cust.empty:
                    c_info = filtered_cust.iloc[0].to_dict()
            
            cust_name = st.text_input("ชื่อผู้ติดต่อ/ชื่อลูกค้า", value=c_info.get('name', ''))
            cust_phone = st.text_input("เบอร์โทรศัพท์", value=c_info.get('phone', ''))

        with col_header2:
            st.subheader("ที่อยู่จัดส่ง/ใบกำกับ")
            cust_addr = st.text_area("ที่อยู่โดยละเอียด", value=c_info.get('address', ''), height=122)

        with col_header3:
            st.subheader("ข้อมูลเอกสาร")
            doc_no = st.text_input("เลขที่เอกสาร", f"QT-{datetime.now().strftime('%Y%m%d-%H%M')}")
            doc_date = st.date_input("วันที่ออกเอกสาร", datetime.now())

    st.divider()

    # --- ส่วนตารางสินค้า (Interactive Table) ---
    st.subheader("รายการสินค้า (สามารถก๊อปวางข้อมูลจาก Excel ได้)")
    
    p_codes = df_products['code'].tolist() if (not df_products.empty and 'code' in df_products.columns) else []
    
    if 'main_table_data' not in st.session_state:
        st.session_state.main_table_data = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา/หน่วย": 0.0, "ส่วนลด": 0.0}] * 10

    edited_df = st.data_editor(
        st.session_state.main_table_data,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัส", options=p_codes),
            "ราคา/หน่วย": st.column_config.NumberColumn(format="%.2f"),
            "ส่วนลด": st.column_config.NumberColumn(format="%.2f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="editor"
    )

    if st.button("🔄 อัปเดตข้อมูลจากฐานข้อมูลสินค้า"):
        new_data = []
        for row in edited_df:
            code = row.get('รหัสสินค้า')
            if code in p_codes:
                p_match = df_products[df_products['code'] == code].iloc[0]
                row['รายการ'] = p_match['description']
                row['หน่วย'] = p_match['unit']
                row['ราคา/หน่วย'] = p_match['price']
            new_data.append(row)
        st.session_state.main_table_data = new_data
        st.rerun()

    # --- ส่วนสรุปยอดเงิน ---
    st.divider()
    calc_df = pd.DataFrame(edited_df)
    calc_df['qty'] = pd.to_numeric(calc_df['จำนวน'], errors='coerce').fillna(0)
    calc_df['price'] = pd.to_numeric(calc_df['ราคา/หน่วย'], errors='coerce').fillna(0)
    calc_df['disc'] = pd.to_numeric(calc_df['ส่วนลด'], errors='coerce').fillna(0)
    
    calc_df['total'] = (calc_df['qty'] * calc_df['price']) - calc_df['disc']
    
    sub_total = calc_df['total'].sum()
    vat = sub_total * 0.07
    grand_total = sub_total + vat

    col_sum1, col_sum2 = st.columns([2, 1])
    with col_sum2:
        st.write(f"**รวมเป็นเงิน:** {sub_total:,.2f} บาท")
        st.write(f"**ภาษีมูลค่าเพิ่ม (7%):** {vat:,.2f} บาท")
        st.markdown(f"### **ยอดรวมสุทธิ: {grand_total:,.2f} บาท**")

# --- TAB: จัดการลูกค้า & สินค้า (เหมือนเดิมแต่เพิ่มความเสถียร) ---
with tab_cust:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    with st.form("add_cust_form", clear_on_submit=True):
        c_id = st.text_input("รหัสลูกค้า (ID)")
        c_name = st.text_input("ชื่อลูกค้า/บริษัท")
        c_phone = st.text_input("เบอร์โทรศัพท์")
        c_addr = st.text_area("ที่อยู่")
        if st.form_submit_button("บันทึกลงฐานข้อมูล Cloud"):
            if c_id and c_name:
                conn.table("customers").upsert({"id": c_id, "name": c_name, "phone": c_phone, "address": c_addr}).execute()
                st.success("บันทึกสำเร็จ!")
                st.rerun()
            else:
                st.warning("กรุณากรอกรหัสและชื่อลูกค้า")
    st.dataframe(df_customers, use_container_width=True)

with tab_prod:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    with st.form("add_prod_form", clear_on_submit=True):
        p_code = st.text_input("รหัสสินค้า")
        p_desc = st.text_input("ชื่อสินค้า/รายละเอียด")
        p_unit = st.text_input("หน่วยนับ")
        p_price = st.number_input("ราคาต่อหน่วย", min_value=0.0)
        if st.form_submit_button("บันทึกลงคลังสินค้า Cloud"):
            if p_code:
                conn.table("products").upsert({"code": p_code, "description": p_desc, "unit": p_unit, "price": p_price}).execute()
                st.success("เพิ่มสินค้าสำเร็จ!")
                st.rerun()
    st.dataframe(df_products, use_container_width=True)
