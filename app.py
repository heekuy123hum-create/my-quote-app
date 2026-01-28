import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import os

# --- 1. การตั้งค่าหน้าตาแอป (UI CONFIG) ---
st.set_page_config(page_title="ระบบใบเสนอราคา Pro (Cloud)", layout="wide")

# ส่วนดึงค่า Config จาก Render (Environment Variables)
MY_SUPABASE_URL = os.environ.get("SUPABASE_URL")
MY_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# ตรวจสอบการเชื่อมต่อ
if not MY_SUPABASE_URL or not MY_SUPABASE_KEY:
    st.error("❌ กรุณาตั้งค่า SUPABASE_URL และ KEY ในหน้า Render ก่อนใช้งาน")
    st.stop()

conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url=MY_SUPABASE_URL,
    key=MY_SUPABASE_KEY
)

# --- 2. ฟังก์ชันจัดการข้อมูล (DATABASE LOGIC) ---
def fetch_data(table):
    try:
        res = conn.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
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
            c_list = ["-- เลือกรหัสลูกค้า --"] + (df_customers['id'].tolist() if not df_customers.empty else [])
            selected_cust_id = st.selectbox("รหัสลูกค้า (ID)", c_list)
            
            # Auto-fill ข้อมูลลูกค้า
            c_info = df_customers[df_customers['id'] == selected_cust_id].iloc[0] if selected_cust_id != "-- เลือกรหัส --" else {}
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
    
    prod_codes = df_products['code'].tolist() if not df_products.empty else []
    
    # สร้างโครงสร้างตาราง 10 แถวเริ่มต้น
    if 'main_table_data' not in st.session_state:
        st.session_state.main_table_data = [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา/หน่วย": 0.0, "ส่วนลด": 0.0}] * 10

    # ใช้ Data Editor เพื่อให้ Copy/Paste ได้
    edited_df = st.data_editor(
        st.session_state.main_table_data,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัส", options=prod_codes),
            "ราคา/หน่วย": st.column_config.NumberColumn(format="%.2f"),
            "ส่วนลด": st.column_config.NumberColumn(format="%.2f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="editor"
    )

    # ปุ่มช่วยดึงข้อมูลสินค้าอัตโนมัติ
    if st.button("🔄 อัปเดตข้อมูลจากฐานข้อมูลสินค้า (Auto-fill สินค้า)"):
        new_data = []
        for row in edited_df:
            code = row.get('รหัสสินค้า')
            if code in prod_codes:
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
    # แปลงค่าเป็นตัวเลขเพื่อคำนวณ
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

    if st.button("💾 บันทึกเอกสารและพิมพ์ PDF"):
        st.success("กำลังส่งคำสั่งพิมพ์ไปยัง Browser...")

# --- TAB: จัดการลูกค้า (Database) ---
with tab_cust:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    with st.expander("➕ เพิ่ม/แก้ไขข้อมูลลูกค้าใหม่"):
        with st.form("add_cust_form", clear_on_submit=True):
            c_id = st.text_input("รหัสลูกค้า (ID)")
            c_name = st.text_input("ชื่อลูกค้า/บริษัท")
            c_phone = st.text_input("เบอร์โทรศัพท์")
            c_addr = st.text_area("ที่อยู่")
            if st.form_submit_button("บันทึกลงฐานข้อมูล Cloud"):
                conn.table("customers").upsert({"id": c_id, "name": c_name, "phone": c_phone, "address": c_addr}).execute()
                st.success("บันทึกสำเร็จ!")
                st.rerun()
    st.dataframe(df_customers, use_container_width=True)

# --- TAB: จัดการสินค้า (Database) ---
with tab_prod:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    with st.expander("➕ เพิ่ม/แก้ไขสินค้าใหม่"):
        with st.form("add_prod_form", clear_on_submit=True):
            p_code = st.text_input("รหัสสินค้า")
            p_desc = st.text_input("ชื่อสินค้า/รายละเอียด")
            p_unit = st.text_input("หน่วยนับ")
            p_price = st.number_input("ราคาต่อหน่วย", min_value=0.0)
            if st.form_submit_button("บันทึกลงคลังสินค้า Cloud"):
                conn.table("products").upsert({"code": p_code, "description": p_desc, "unit": p_unit, "price": p_price}).execute()
                st.success("เพิ่มสินค้าสำเร็จ!")
                st.rerun()
    st.dataframe(df_products, use_container_width=True)