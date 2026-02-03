import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

# ==========================================
# 1. DATABASE SYSTEM & CONFIG
# ==========================================
st.set_page_config(page_title="SIWAKIT Enterprise System", layout="wide")

# ชื่อไฟล์สำหรับบันทึกข้อมูลถาวร
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"

# ฟังก์ชันโหลดข้อมูล (ปรับปรุง Logic ให้โหลดแม่นยำและไม่คืนค่าเดิม)
def load_data():
    # --- 1. โหลดลูกค้า ---
    if "db_customers" not in st.session_state:
        if os.path.exists(CUST_FILE):
            try:
                st.session_state.db_customers = pd.read_csv(CUST_FILE)
            except:
                # กรณีไฟล์เสีย ให้สร้างใหม่
                st.session_state.db_customers = pd.DataFrame([{"รหัส": "C001", "ชื่อบริษัท": "ตัวอย่าง", "ผู้ติดต่อ": "สมชาย", "ที่อยู่": "กทม.", "โทร": "081", "แฟกซ์": "-"}])
        else:
            # กรณีไม่มีไฟล์เลย (เปิดครั้งแรกสุด)
            st.session_state.db_customers = pd.DataFrame([
                {"รหัส": "C001", "ชื่อบริษัท": "บริษัท ตัวอย่าง จำกัด", "ผู้ติดต่อ": "คุณสมชาย", "ที่อยู่": "123 กทม.", "โทร": "081-111-1111", "แฟกซ์": "02-222-2222"},
                {"รหัส": "C002", "ชื่อบริษัท": "หจก. ทดสอบระบบ", "ผู้ติดต่อ": "คุณสมหญิง", "ที่อยู่": "456 เชียงใหม่", "โทร": "089-999-9999", "แฟกซ์": "-"}
            ])
        
        # เพิ่มคอลัมน์ 'ลบ' ถ้ายังไม่มี
        if 'ลบ' not in st.session_state.db_customers.columns:
            st.session_state.db_customers.insert(0, 'ลบ', False)

    # --- 2. โหลดสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                st.session_state.db_products = pd.read_csv(PROD_FILE)
            except:
                st.session_state.db_products = pd.DataFrame([{"รหัสสินค้า": "P001", "รายการ": "สินค้า A", "ราคา": 100, "หน่วย": "ชิ้น"}])
        else:
            st.session_state.db_products = pd.DataFrame([
                {"รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง A", "ราคา": 1500.0, "หน่วย": "ชิ้น"},
                {"รหัสสินค้า": "P002", "รายการ": "สินค้าตัวอย่าง B", "ราคา": 2500.0, "หน่วย": "เครื่อง"},
                {"รหัสสินค้า": "P003", "รายการ": "ค่าบริการติดตั้ง", "ราคา": 5000.0, "หน่วย": "งาน"}
            ])
            
        # เพิ่มคอลัมน์ 'ลบ' ถ้ายังไม่มี
        if 'ลบ' not in st.session_state.db_products.columns:
            st.session_state.db_products.insert(0, 'ลบ', False)

# ฟังก์ชันบันทึกข้อมูลลง CSV (ตัดช่อง 'ลบ' ออกก่อนเซฟ)
def save_data(df, filename):
    df_to_save = df.copy()
    if 'ลบ' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['ลบ'])
    df_to_save.to_csv(filename, index=False)

# เรียกใช้โหลดข้อมูลทันที
load_data()

# สร้างตารางว่างสำหรับหน้า Quotation (ถ้ายังไม่มี)
if "grid_df" not in st.session_state:
    st.session_state.grid_df = pd.DataFrame([
        {"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}
    ] * 20)

def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val else 0.0
    except: return 0.0

# ==========================================
# 2. PDF ENGINE (ระบบสร้าง PDF)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # จัดการ Font
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        pdf.add_font('THSarabun', 'B', font_path)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # โลโก้
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
            
    # ข้อมูลบริษัท (Header ซ้าย)
    pdf.set_xy(35, 10)
    pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(100, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # เลขที่เอกสาร (Header ขวา)
    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0)
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    # หัวเรื่องใหญ่
    pdf.set_y(42)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # ข้อมูลลูกค้าและเงื่อนไข
    pdf.set_font(use_f, '', 14)
    pdf.ln(2)
    start_info_y = pdf.get_y()
    
    pdf.set_xy(10, start_info_y)
    pdf.multi_cell(115, 6, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}", 0, 'L')
    y_left = pdf.get_y()
    
    pdf.set_xy(130, start_info_y)
    pdf.multi_cell(75, 6, f"วันที่กำหนดส่ง: {d['due_date']}\nยืนราคา (วัน): {d['valid_days']}  Expire Date: {d['exp_date']}\nเครดิต (วัน): {d['credit']}", 0, 'L')
    y_right = pdf.get_y()
    
    pdf.set_y(max(y_left, y_right) + 5)

    # ตารางสินค้า
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 11)
    
    w = [15, 75, 15, 15, 25, 15, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 11)
    row_height = 6.0
    
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
            else: vals = [""] * 7
        else: vals = [""] * 7
            
        for j in range(7):
            align = 'L' if j == 1 else 'C'
            if j == 6: align = 'R'
            pdf.cell(w[j], row_height, vals[j], 1, 0, align)
        pdf.ln()

    # Footer
    pdf.ln(2)
    footer_y = pdf.get_y()
    
    pdf.set_xy(10, footer_y)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12)
    pdf.set_x(10)
    pdf.multi_cell(105, 5, remark_text, 0, 'L')
    
    curr_y = footer_y
    label_x = 125
    val_x = 175

    def add_total_row(label, value, is_bold=False, is_red=False):
        nonlocal curr_y
        pdf.set_font(use_f, 'B' if is_bold else '', 13 if is_bold else 12)
        if is_red: pdf.set_text_color(180, 0, 0)
        else: pdf.set_text_color(0, 0, 0)
        
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

    # ลายเซ็น
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

# ==========================================
# 3. UI DISPLAY (ส่วนหน้าจอ)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 คลังสินค้า"])

# --- TAB 1: สร้างใบเสนอราคา ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัท", "SIWAKIT", key="my_comp_in")
        my_addr = st.text_input("ที่อยู่บริษัท", "123/45 ถนนตัวอย่าง แขวง... เขต...", key="my_addr_in")
        my_tel = st.text_input("โทรศัพท์", "02-xxx-xxxx", key="my_tel_in")
        my_fax = st.text_input("โทรสาร", "-", key="my_fax_in")
        my_tax = st.text_input("เลขผู้เสียภาษี", "1234567890123", key="my_tax_in")
    
    with col2:
        st.subheader("📄 รายละเอียดเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        doc_date = st.text_input("วันที่ออกเอกสาร", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("วันที่กำหนดส่ง", "7 วัน")
        v_col1, v_col2 = st.columns(2)
        valid_days = v_col1.text_input("ยืนราคา (วัน)", "30")
        exp_date = v_col2.text_input("Expire Date", datetime.now().strftime('%d/%m/%Y'))
        credit = st.text_input("เครดิต (วัน)", "30")

    st.divider()

    c_h1, c_h2 = st.columns([1, 1])
    with c_h1: st.subheader("👤 ข้อมูลลูกค้า")
    with c_h2: 
        # [จุดที่แก้] ดึงข้อมูลสดจาก Session State เสมอ (กรอกปุ๊บ มาปั๊บ)
        current_customers = st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist()
        c_list = ["-- พิมพ์เอง --"] + [str(x) for x in current_customers if str(x).strip() != ""]
        sel_c = st.selectbox("📥 ดึงข้อมูลลูกค้าเก่า", c_list, key="cust_selector_tab1")

    # Auto-fill ลูกค้า
    def_name, def_cont, def_addr, def_tel, def_fax = "", "", "", "", ""
    if sel_c != "-- พิมพ์เอง --":
        # ค้นหาข้อมูลใน Session State
        found_c = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == sel_c]
        if not found_c.empty:
            row_c = found_c.iloc[0]
            def_name, def_cont, def_addr, def_tel, def_fax = row_c['ชื่อบริษัท'], row_c['ผู้ติดต่อ'], row_c['ที่อยู่'], row_c['โทร'], row_c['แฟกซ์']

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        c_name = st.text_input("ชื่อบริษัทลูกค้า", value=def_name)
        contact = st.text_input("ชื่อผู้ติดต่อ", value=def_cont)
        c_addr = st.text_area("ที่อยู่จัดส่ง/วางบิล", value=def_addr, height=70)
    with c_col2:
        st.write("<br><br>", unsafe_allow_html=True)
        c_tel = st.text_input("เบอร์โทรศัพท์ลูกค้า", value=def_tel)
        c_fax = st.text_input("เบอร์แฟกซ์ลูกค้า", value=def_fax)

    # ส่วนตารางสินค้า
    st.subheader("📦 รายการสินค้า")
    
    # [จุดที่แก้] ดึงรหัสสินค้าสดจาก Session State เสมอ
    current_products = st.session_state.db_products['รหัสสินค้า'].dropna().unique().tolist()
    p_codes = [str(x) for x in current_products if str(x).strip() != ""]
    
    current_df = st.session_state.grid_df.fillna(0)
    
    # ตาราง Editor
    edited_df = st.data_editor(
        current_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัสสินค้า", options=p_codes)
        },
        num_rows="dynamic",
        use_container_width=True,
        key="editor_main"
    )

    # Logic การดึงข้อมูลสินค้าอัตโนมัติ
    needs_rerun = False
    for idx, row in edited_df.iterrows():
        code = str(row['รหัสสินค้า'])
        if code and code in p_codes:
            found_prod = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'].astype(str) == code]
            
            if not found_prod.empty:
                p_info = found_prod.iloc[0]
                # ถ้าชื่อรายการไม่ตรง (แสดงว่าเพิ่งเลือกใหม่) ให้อัปเดต
                if row['รายการ'] != p_info['รายการ']:
                    edited_df.at[idx, 'รายการ'] = p_info['รายการ']
                    edited_df.at[idx, 'หน่วย'] = p_info['หน่วย']
                    edited_df.at[idx, 'ราคา'] = p_info['ราคา']
                    needs_rerun = True

    if needs_rerun:
        st.session_state.grid_df = edited_df
        st.rerun() # รีเฟรชทันทีเมื่อดึงข้อมูลเสร็จ
    else:
        st.session_state.grid_df = edited_df

    # คำนวณเงิน
    calc_df = edited_df.copy()
    calc_df['q'] = calc_df['จำนวน'].apply(to_num)
    calc_df['p'] = calc_df['ราคา'].apply(to_num)
    calc_df['d'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['รวมเงิน'] = (calc_df['q'] * calc_df['p']) - calc_df['d']
    
    sum_gross = (calc_df['q'] * calc_df['p']).sum()
    sum_disc = calc_df['d'].sum()
    sum_sub = calc_df['รวมเงิน'].sum()

    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        remark = st.text_area("📝 หมายเหตุ", value="1. สินค้ารับประกัน 1 ปี\n2. กำหนดยืนราคาตามที่ระบุในเอกสาร")
    with f_col2:
        st.write("### สรุปยอดเงิน")
        has_vat = st.checkbox("✅ คิด VAT 7%", value=True)
        vat_val = int(sum_sub * 0.07) if has_vat else 0.0
        grand_total = sum_sub + vat_val

        st.write(f"รวมเป็นเงิน: {sum_gross:,.2f}")
        st.write(f"ส่วนลดทั้งหมด: -{sum_disc:,.2f}")
        st.write(f"ยอดหลังหักส่วนลด: {sum_sub:,.2f}")
        if has_vat:
            st.write(f"ภาษีมูลค่าเพิ่ม 7%: {vat_val:,.2f}")
        st.metric("ยอดรวมทั้งสิ้น", f"{grand_total:,.2f} บาท")

    s_col1, s_col2, s_col3 = st.columns(3)
    s1 = s_col1.text_input("ชื่อลูกค้า")
    s2 = s_col2.text_input("ชื่อพนักงานขาย")
    s3 = s_col3.text_input("ชื่อผู้จัดการ")

    if st.button("🚀 สร้างและดาวน์โหลด PDF", type="primary", use_container_width=True):
        d_pdf = {
            "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
            "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "valid_days": valid_days,
            "exp_date": exp_date, "credit": credit, "c_name": c_name, "contact": contact,
            "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax
        }
        res_pdf = create_pdf(
            d_pdf, calc_df, 
            {"gross": sum_gross, "discount": sum_disc, "subtotal": sum_sub, "vat": vat_val, "grand_total": grand_total},
            {"s1": s1, "s2": s2, "s3": s3},
            remark, has_vat
        )
        st.success("สร้าง PDF สำเร็จ!")
        st.download_button("📥 คลิกเพื่อดาวน์โหลด", res_pdf, f"{doc_no}.pdf", "application/pdf")

# --- TAB 2: จัดการลูกค้า ---
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    st.info("💡 วิธีลบ: ติ๊กถูกที่ช่อง 'ลบ' หน้าชื่อที่ต้องการ แล้วกดปุ่มสีแดง 'ลบรายการที่เลือก'")

    # Clean ข้อมูลก่อนแสดง
    if not st.session_state.db_customers.empty:
        if 'ลบ' not in st.session_state.db_customers.columns:
            st.session_state.db_customers.insert(0, 'ลบ', False)
        st.session_state.db_customers = st.session_state.db_customers.fillna("")
    
    edited_customers = st.data_editor(
        st.session_state.db_customers, 
        num_rows="dynamic", 
        use_container_width=True,
        key="db_cust_editor_manual" 
    )
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🗑️ ลบรายการที่เลือก (ลูกค้า)", type="secondary", use_container_width=True):
            # 1. กรองเอาเฉพาะที่ไม่ได้ติ๊ก
            new_df = edited_customers[edited_customers['ลบ'] == False]
            # 2. บันทึก
            save_data(new_df, CUST_FILE)
            # 3. อัปเดต Memory
            st.session_state.db_customers = new_df
            # 4. Rerun เพื่อให้ Tab 1 เห็นค่าใหม่ทันที
            st.rerun()

    with c_btn2:
        if st.button("💾 บันทึกการเปลี่ยนแปลง (ลูกค้า)", type="primary", use_container_width=True):
            # 1. บันทึก
            save_data(edited_customers, CUST_FILE)
            # 2. อัปเดต Memory
            st.session_state.db_customers = edited_customers
            # 3. แจ้งเตือนและ Rerun
            st.success("✅ บันทึกข้อมูลลูกค้าเรียบร้อย!")
            st.rerun()

# --- TAB 3: จัดการสินค้า ---
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    st.info("💡 วิธีลบ: ติ๊กถูกที่ช่อง 'ลบ' หน้าชื่อที่ต้องการ แล้วกดปุ่มสีแดง 'ลบรายการที่เลือก'")
    
    if not st.session_state.db_products.empty:
        if 'ลบ' not in st.session_state.db_products.columns:
            st.session_state.db_products.insert(0, 'ลบ', False)
        if 'ราคา' in st.session_state.db_products.columns:
            st.session_state.db_products['ราคา'] = st.session_state.db_products['ราคา'].fillna(0.0)
        st.session_state.db_products = st.session_state.db_products.fillna("")
    
    edited_products = st.data_editor(
        st.session_state.db_products, 
        num_rows="dynamic", 
        use_container_width=True,
        key="db_prod_editor_manual"
    )
    
    p_btn1, p_btn2 = st.columns(2)
    with p_btn1:
        if st.button("🗑️ ลบรายการที่เลือก (สินค้า)", type="secondary", use_container_width=True):
            new_df_p = edited_products[edited_products['ลบ'] == False]
            save_data(new_df_p, PROD_FILE)
            st.session_state.db_products = new_df_p
            st.rerun()

    with p_btn2:
        if st.button("💾 บันทึกการเปลี่ยนแปลง (สินค้า)", type="primary", use_container_width=True):
            save_data(edited_products, PROD_FILE) 
            st.session_state.db_products = edited_products
            st.success("✅ บันทึกข้อมูลสินค้าเรียบร้อย!")
            st.rerun()
