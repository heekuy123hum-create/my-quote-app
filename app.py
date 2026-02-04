import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

# ==========================================
# 1. ตั้งค่าระบบและ Database
# ==========================================
st.set_page_config(page_title="ระบบออกใบเสนอราคา", layout="wide", page_icon="🏢")

# ชื่อไฟล์ Database
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"

# เริ่มต้นตัวแปร Session State (เก็บค่าระหว่างการใช้งาน)
if "grid_df" not in st.session_state:
    # สร้างตารางเปล่า 20 บรรทัดสำหรับหน้าเสนอราคา
    st.session_state.grid_df = pd.DataFrame(
        [{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0.0, "ส่วนลด": 0.0}] * 20
    )

# ==========================================
# 2. ฟังก์ชันจัดการข้อมูล (LOAD & SAVE)
# ==========================================
def load_data():
    # --- โหลดข้อมูลลูกค้า ---
    if "db_customers" not in st.session_state:
        if os.path.exists(CUST_FILE):
            try:
                # ใช้ utf-8-sig แก้ปัญหาภาษาไทยใน Excel
                temp_df = pd.read_csv(CUST_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df.columns: temp_df = temp_df.drop(columns=['Unnamed: 0'])
                # แปลงรหัสให้เป็น String ป้องกัน Error
                temp_df['รหัส'] = temp_df['รหัส'].astype(str)
                st.session_state.db_customers = temp_df
            except:
                st.session_state.db_customers = pd.DataFrame(columns=["รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            # ข้อมูลตัวอย่างเริ่มต้น
            st.session_state.db_customers = pd.DataFrame([
                {"รหัส": "C001", "ชื่อบริษัท": "ลูกค้าทั่วไป (เงินสด)", "ผู้ติดต่อ": "-", "ที่อยู่": "-", "โทร": "-", "แฟกซ์": "-"},
                {"รหัส": "C002", "ชื่อบริษัท": "บริษัท ตัวอย่าง จำกัด", "ผู้ติดต่อ": "คุณสมชาย", "ที่อยู่": "123 กทม.", "โทร": "081-000-0000", "แฟกซ์": "-"}
            ])
        
        # เพิ่มคอลัมน์ 'ลบ' ไว้หน้าสุดถ้ายังไม่มี
        if 'ลบ' not in st.session_state.db_customers.columns:
            st.session_state.db_customers.insert(0, 'ลบ', False)

    # --- โหลดข้อมูลสินค้า ---
    if "db_products" not in st.session_state:
        if os.path.exists(PROD_FILE):
            try:
                temp_df_p = pd.read_csv(PROD_FILE, encoding='utf-8-sig')
                if 'Unnamed: 0' in temp_df_p.columns: temp_df_p = temp_df_p.drop(columns=['Unnamed: 0'])
                temp_df_p['รหัสสินค้า'] = temp_df_p['รหัสสินค้า'].astype(str)
                st.session_state.db_products = temp_df_p
            except:
                st.session_state.db_products = pd.DataFrame(columns=["รหัสสินค้า", "รายการ", "ราคา", "หน่วย"])
        else:
            # ข้อมูลสินค้าตัวอย่าง
            st.session_state.db_products = pd.DataFrame([
                {"รหัสสินค้า": "P001", "รายการ": "ค่าบริการ", "ราคา": 1000.0, "หน่วย": "งาน"},
                {"รหัสสินค้า": "P002", "รายการ": "สินค้าตัวอย่าง A", "ราคา": 500.0, "หน่วย": "ชิ้น"}
            ])
            
        if 'ลบ' not in st.session_state.db_products.columns:
            st.session_state.db_products.insert(0, 'ลบ', False)

def save_data(df, filename):
    """บันทึกข้อมูลลง CSV พร้อมรองรับภาษาไทย"""
    df_save = df.copy()
    # ลบคอลัมน์ checkbox ก่อนบันทึก
    if 'ลบ' in df_save.columns: df_save = df_save.drop(columns=['ลบ'])
    if 'Unnamed: 0' in df_save.columns: df_save = df_save.drop(columns=['Unnamed: 0'])
    
    df_save.to_csv(filename, index=False, encoding='utf-8-sig')

# เรียกโหลดข้อมูลทันทีที่เปิดแอป
load_data()

# ฟังก์ชันแปลงตัวเลข (กัน Error)
def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val)
    except:
        return 0.0

# ==========================================
# 3. ระบบสร้าง PDF (ตามดีไซน์ที่คุณส่งมา)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # Font Setup
    font_path = "THSarabunNew.ttf"
    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path, uni=True)
        pdf.add_font('THSarabun', 'B', font_path, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # โลโก้บริษัท
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
            
    # Header: ข้อมูลฝั่งเรา (ซ้าย)
    pdf.set_xy(35, 10)
    pdf.set_font(use_f, 'B', 14)
    header_text = f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}"
    pdf.multi_cell(100, 6, header_text, 0, 'L')

    # Header: เลขที่เอกสาร (ขวา)
    pdf.set_xy(145, 10)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0) # กรอบเลขที่
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    # Title
    pdf.set_y(42)
    pdf.set_font(use_f, 'B', 24)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # ข้อมูลลูกค้า & เงื่อนไข (จัดวาง 2 ฝั่ง)
    pdf.set_font(use_f, '', 14)
    pdf.ln(2)
    start_info_y = pdf.get_y()
    
    # ฝั่งลูกค้า
    pdf.set_xy(10, start_info_y)
    cust_info = f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}"
    pdf.multi_cell(115, 6, cust_info, 0, 'L')
    y_left = pdf.get_y()
    
    # ฝั่งเงื่อนไข
    pdf.set_xy(130, start_info_y)
    terms_info = f"วันที่กำหนดส่ง: {d['due_date']}\nยืนราคา (วัน): {d['valid_days']}  Expire Date: {d['exp_date']}\nเครดิต (วัน): {d['credit']}"
    pdf.multi_cell(75, 6, terms_info, 0, 'L')
    y_right = pdf.get_y()
    
    # ระยะห่างก่อนตาราง
    pdf.set_y(max(y_left, y_right) + 5)

    # ตารางสินค้า (Fix 20 บรรทัด)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(use_f, 'B', 11)
    
    w = [15, 75, 15, 15, 25, 15, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    
    for i in range(len(headers)):
        pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font(use_f, '', 11)
    row_height = 6.0
    
    # วนลูปสร้างบรรทัดตาราง 20 บรรทัดเสมอ (ตามความต้องการที่ว่าห้ามหาย)
    for i in range(20):
        if i < len(items_df):
            row = items_df.iloc[i]
            # เช็คว่ามีรายการไหม
            item_name = str(row.get('รายการ','')).strip()
            if item_name != "" and item_name != "0":
                vals = [
                    str(row.get('รหัสสินค้า','')),
                    item_name,
                    f"{to_num(row.get('จำนวน')):,.0f}",
                    str(row.get('หน่วย','')),
                    f"{to_num(row.get('ราคา')):,.0f}",
                    f"{to_num(row.get('ส่วนลด')):,.0f}",
                    f"{to_num(row.get('รวมเงิน',0)):,.0f}"
                ]
            else:
                vals = [""] * 7
        else:
            vals = [""] * 7
            
        for j in range(7):
            align = 'L' if j == 1 else 'C'
            if j == 6: align = 'R'
            pdf.cell(w[j], row_height, vals[j], 1, 0, align)
        pdf.ln()

    # Footer: สรุปยอดเงิน
    pdf.ln(2)
    footer_y = pdf.get_y()
    
    # หมายเหตุ (ซ้าย)
    pdf.set_xy(10, footer_y)
    pdf.set_font(use_f, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12)
    pdf.set_x(10)
    pdf.multi_cell(105, 5, remark_text, 0, 'L')
    
    # ยอดคำนวณ (ขวา)
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

    # ลายเซ็น (ท้ายหน้า)
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
# 4. ส่วนแสดงผล (User Interface)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 ฐานข้อมูลสินค้า"])

# ------------------------------------------------------------------
# TAB 1: หน้าออกเอกสาร
# ------------------------------------------------------------------
with tab1:
    # ส่วนหัว: ข้อมูลบริษัทเรา & ข้อมูลเอกสาร
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("ข้อมูลผู้ขาย (เรา)")
        my_comp = st.text_input("ชื่อบริษัท", "บริษัท สยามวาณิชย์ จำกัด", key="my_comp")
        my_addr = st.text_input("ที่อยู่", "123 กทม. 10110", key="my_addr")
        r1, r2 = st.columns(2)
        my_tel = r1.text_input("โทรศัพท์", "02-123-4567", key="my_tel")
        my_tax = r2.text_input("เลขผู้เสียภาษี", "0105551234567", key="my_tax")
        my_fax = st.text_input("แฟกซ์", "-", key="my_fax")
        
    with c2:
        st.subheader("ข้อมูลเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%Y%m%d')}-001")
        doc_date = st.text_input("วันที่", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("กำหนดส่งของ", "ภายใน 7 วัน")
        
        r3, r4 = st.columns(2)
        valid_days = r3.number_input("ยืนราคา (วัน)", value=30)
        credit = r4.number_input("เครดิต (วัน)", value=30)
        exp_date = st.text_input("วันหมดอายุใบเสนอราคา", datetime.now().strftime('%d/%m/%Y'))

    st.divider()

    # ส่วนลูกค้า: เลือกจาก Database แล้ว Auto-fill
    col_cust_head, col_cust_sel = st.columns([1, 1])
    with col_cust_head: st.subheader("ข้อมูลลูกค้า")
    with col_cust_sel:
        # ดึงรายชื่อลูกค้าจาก Session State (ที่อัปเดตแล้ว)
        cust_list = ["-- พิมพ์เอง --"] + sorted(st.session_state.db_customers['ชื่อบริษัท'].dropna().unique().tolist())
        selected_cust = st.selectbox("🔍 ค้นหาลูกค้าเก่า", cust_list)

    # Logic การเติมคำอัตโนมัติ
    c_name_val, c_cont_val, c_addr_val, c_tel_val, c_fax_val = "", "", "", "", ""
    if selected_cust != "-- พิมพ์เอง --":
        # Filter หาแถวที่ชื่อตรงกัน
        found = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == selected_cust]
        if not found.empty:
            row = found.iloc[0]
            c_name_val = row['ชื่อบริษัท']
            c_cont_val = row['ผู้ติดต่อ']
            c_addr_val = row['ที่อยู่']
            c_tel_val = row['โทร']
            c_fax_val = row['แฟกซ์']

    # ฟอร์มกรอกข้อมูลลูกค้า
    cc1, cc2 = st.columns(2)
    with cc1:
        c_name = st.text_input("ชื่อลูกค้า/บริษัท", value=c_name_val)
        c_contact = st.text_input("ผู้ติดต่อ", value=c_cont_val)
        c_addr = st.text_area("ที่อยู่ลูกค้า", value=c_addr_val, height=100)
    with cc2:
        c_tel = st.text_input("เบอร์โทร", value=c_tel_val)
        c_fax = st.text_input("เบอร์แฟกซ์", value=c_fax_val)

    st.divider()
    
    # ส่วนรายการสินค้า (Data Editor)
    st.subheader("รายการสินค้า")
    
    # เตรียม Dropdown รหัสสินค้า
    prod_codes = sorted(st.session_state.db_products['รหัสสินค้า'].dropna().unique().astype(str).tolist())
    
    # แสดงตารางให้แก้ไขได้ (ซ่อน index ด้วย hide_index=True)
    edited_df = st.data_editor(
        st.session_state.grid_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn("รหัสสินค้า", options=prod_codes, width="medium"),
            "รายการ": st.column_config.TextColumn("รายการสินค้า", width="large"),
            "จำนวน": st.column_config.NumberColumn("จำนวน", min_value=0, format="%.2f"),
            "ราคา": st.column_config.NumberColumn("ราคา/หน่วย", min_value=0, format="%.2f"),
            "ส่วนลด": st.column_config.NumberColumn("ส่วนลด (บาท)", min_value=0, format="%.2f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,  # ซ่อนตัวเลขแถว
        key="quotation_grid"
    )

    # Logic: ดึงข้อมูลสินค้าอัตโนมัติเมื่อเลือกรหัส
    need_rerun = False
    for i, row in edited_df.iterrows():
        code = str(row['รหัสสินค้า'])
        if code and code in prod_codes:
            # เช็คใน Database
            p_data = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'] == code]
            if not p_data.empty:
                p_row = p_data.iloc[0]
                # ถ้าชื่อรายการในตารางยังว่าง หรือไม่ตรงกับ Database ให้เติมใหม่
                if row['รายการ'] != p_row['รายการ']:
                    edited_df.at[i, 'รายการ'] = p_row['รายการ']
                    edited_df.at[i, 'หน่วย'] = p_row['หน่วย']
                    edited_df.at[i, 'ราคา'] = p_row['ราคา']
                    need_rerun = True
    
    if need_rerun:
        st.session_state.grid_df = edited_df
        st.rerun()
    else:
        st.session_state.grid_df = edited_df

    # คำนวณยอดเงิน (สำหรับส่งเข้า PDF)
    calc_df = edited_df.copy()
    calc_df['qty'] = calc_df['จำนวน'].apply(to_num)
    calc_df['price'] = calc_df['ราคา'].apply(to_num)
    calc_df['disc'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['รวมเงิน'] = (calc_df['qty'] * calc_df['price']) - calc_df['disc'] # ใช้ชื่อคอลัมน์ภาษาไทยให้ตรงกับ create_pdf
    
    sum_gross = (calc_df['qty'] * calc_df['price']).sum()
    sum_disc = calc_df['disc'].sum()
    sum_subtotal = calc_df['รวมเงิน'].sum()

    # ส่วนสรุปและลายเซ็น
    foot1, foot2 = st.columns([2, 1])
    with foot1:
        remark = st.text_area("หมายเหตุ", "1. กำหนดยืนราคา 30 วัน\n2. สินค้ารับประกัน 1 ปี\n3. ชำระเงินมัดจำ 50% ณ วันสั่งซื้อ", height=150)
        
        st.write("---")
        st.caption("ลายเซ็นท้ายกระดาษ")
        s1, s2, s3 = st.columns(3)
        sig_cust = s1.text_input("ชื่อลูกค้า (เซ็น)", c_contact)
        sig_sale = s2.text_input("พนักงานขาย", "แอดมิน")
        sig_mgr = s3.text_input("ผู้จัดการ", "สมศักดิ์")

    with foot2:
        st.write("#### สรุปยอดเงิน")
        use_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)
        
        vat_amount = sum_subtotal * 0.07 if use_vat else 0
        grand_total = sum_subtotal + vat_amount
        
        st.write(f"รวมเป็นเงิน: {sum_gross:,.2f}")
        st.write(f"หักส่วนลด: -{sum_disc:,.2f}")
        st.markdown(f"**ยอดหลังหักส่วนลด: {sum_subtotal:,.2f}**")
        if use_vat:
            st.write(f"VAT 7%: {vat_amount:,.2f}")
        
        st.metric("ยอดสุทธิ (Grand Total)", f"{grand_total:,.2f} บาท")
        
        # ปุ่มสร้าง PDF (เต็มจอสำหรับมือถือ)
        if st.button("🖨️ สร้าง PDF และ ดาวน์โหลด", type="primary", use_container_width=True):
            if c_name == "":
                st.error("กรุณาระบุชื่อลูกค้าก่อนสร้างเอกสาร")
            else:
                pdf_bytes = create_pdf(
                    d={
                        "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
                        "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date,
                        "valid_days": valid_days, "credit": credit, "exp_date": exp_date,
                        "c_name": c_name, "contact": c_contact, "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax
                    },
                    items_df=calc_df,
                    summary={"gross": sum_gross, "discount": sum_disc, "subtotal": sum_subtotal, "vat": vat_amount, "grand_total": grand_total},
                    sigs={"s1": sig_cust, "s2": sig_sale, "s3": sig_mgr},
                    remark_text=remark,
                    show_vat_line=use_vat
                )
                st.success("สร้างเอกสารสำเร็จ!")
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ PDF",
                    data=pdf_bytes,
                    file_name=f"Quotation-{doc_no}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# ------------------------------------------------------------------
# TAB 2: ฐานข้อมูลลูกค้า (Fix Sync & Mobile)
# ------------------------------------------------------------------
with tab2:
    st.header("จัดการฐานข้อมูลลูกค้า")
    
    # ใช้ Data Editor (ซ่อน index)
    edited_cust = st.data_editor(
        st.session_state.db_customers,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,  # ซ่อนเลขแถว 0, 1, 2
        column_config={
            "ลบ": st.column_config.CheckboxColumn("ลบ", help="ติ๊กเพื่อลบแถวนี้", default=False),
            "รหัส": st.column_config.TextColumn("รหัส", width="small"),
            "ชื่อบริษัท": st.column_config.TextColumn("ชื่อบริษัท", width="large"),
        },
        key="cust_editor"
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 บันทึกข้อมูลลูกค้า", type="primary", use_container_width=True):
            # กรองแถวที่ติ๊กลบออก
            to_save = edited_cust[edited_cust['ลบ'] == False].copy()
            
            # บันทึกไฟล์
            save_data(to_save, CUST_FILE)
            
            # อัปเดต Session State
            st.session_state.db_customers = to_save
            
            # แจ้งเตือน
            st.toast("บันทึกข้อมูลลูกค้าเรียบร้อย!", icon="✅")
            
            # *** สำคัญ: Rerun เพื่อให้ Tab 1 เห็นข้อมูลใหม่ทันที ***
            st.rerun()

    with col_btn2:
        if st.button("❌ รีโหลด/ยกเลิก", use_container_width=True):
            del st.session_state.db_customers
            st.rerun()

# ------------------------------------------------------------------
# TAB 3: ฐานข้อมูลสินค้า (Fix Sync & Mobile)
# ------------------------------------------------------------------
with tab3:
    st.header("จัดการฐานข้อมูลสินค้า")
    
    # ใช้ Data Editor (ซ่อน index)
    edited_prod = st.data_editor(
        st.session_state.db_products,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,  # ซ่อนเลขแถว 0, 1, 2
        column_config={
            "ลบ": st.column_config.CheckboxColumn("ลบ", default=False),
            "รหัสสินค้า": st.column_config.TextColumn("รหัส", width="small"),
            "รายการ": st.column_config.TextColumn("ชื่อสินค้า", width="large"),
            "ราคา": st.column_config.NumberColumn("ราคา", format="%.2f"),
        },
        key="prod_editor"
    )

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("💾 บันทึกสินค้า", type="primary", use_container_width=True):
            # กรองแถวที่ติ๊กลบออก
            to_save_p = edited_prod[edited_prod['ลบ'] == False].copy()
            
            # บันทึกไฟล์
            save_data(to_save_p, PROD_FILE)
            
            # อัปเดต Session State
            st.session_state.db_products = to_save_p
            
            # แจ้งเตือน
            st.toast("บันทึกข้อมูลสินค้าเรียบร้อย!", icon="✅")
            
            # *** สำคัญ: Rerun เพื่อให้ Tab 1 เห็นข้อมูลใหม่ทันที ***
            st.rerun()

    with col_p2:
        if st.button("❌ รีโหลดสินค้าใหม่", use_container_width=True):
            del st.session_state.db_products
            st.rerun()
