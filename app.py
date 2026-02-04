import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

# ==========================================
# 1. ตั้งค่าหน้าเว็บและ Session State (ห้ามตัดออก)
# ==========================================
st.set_page_config(page_title="ระบบออกใบเสนอราคา (Full Version)", layout="wide", page_icon="🏢")

# ชื่อไฟล์ Database
CUST_FILE = "database_customers.csv"
PROD_FILE = "database_products.csv"

# เริ่มต้นตัวแปร Session State (เก็บค่าระหว่างการใช้งาน)
if "grid_df" not in st.session_state:
    # สร้างตารางเปล่า 20 บรรทัด
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
                st.error(f"ไฟล์ {CUST_FILE} เสียหาย กำลังสร้างใหม่...")
                st.session_state.db_customers = pd.DataFrame(columns=["รหัส", "ชื่อบริษัท", "ผู้ติดต่อ", "ที่อยู่", "โทร", "แฟกซ์"])
        else:
            # ข้อมูลตัวอย่างเริ่มต้น
            st.session_state.db_customers = pd.DataFrame([
                {"รหัส": "C001", "ชื่อบริษัท": "ลูกค้าทั่วไป (เงินสด)", "ผู้ติดต่อ": "-", "ที่อยู่": "-", "โทร": "-", "แฟกซ์": "-"},
                {"รหัส": "C002", "ชื่อบริษัท": "บริษัท ตัวอย่าง จำกัด", "ผู้ติดต่อ": "คุณสมชาย", "ที่อยู่": "123 กทม.", "โทร": "081-000-0000", "แฟกซ์": "-"}
            ])
        
        # เพิ่มคอลัมน์ 'ลบ' ถ้ายังไม่มี
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
# 3. ระบบสร้าง PDF (รองรับภาษาไทย)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # 3.1 ตั้งค่าฟอนต์ (ต้องมีไฟล์ THSarabunNew.ttf ในโฟลเดอร์เดียวกับโค้ด)
    font_path = "THSarabunNew.ttf" 
    has_font = os.path.exists(font_path)
    if has_font:
        pdf.add_font('THSarabun', '', font_path, uni=True)
        pdf.add_font('THSarabun', 'B', font_path, uni=True)
        main_font = 'THSarabun'
    else:
        main_font = 'Arial' # Fallback ถ้าไม่มีฟอนต์ไทย

    # 3.2 ใส่โลโก้ (ถ้ามีไฟล์ logo.png/jpg)
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=8, w=25)
            break

    # 3.3 ส่วนหัวเอกสาร (Header)
    pdf.set_xy(38, 10)
    pdf.set_font(main_font, 'B', 16)
    pdf.cell(0, 8, d['my_comp'], 0, 1, 'L')
    
    pdf.set_x(38)
    pdf.set_font(main_font, '', 12)
    pdf.multi_cell(100, 5, f"{d['my_addr']}\nโทร: {d['my_tel']} แฟกซ์: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    # กล่องเลขที่เอกสารขวาบน
    pdf.set_xy(140, 10)
    pdf.set_font(main_font, 'B', 12)
    pdf.cell(60, 20, "", 1) # กรอบ
    pdf.set_xy(142, 12)
    pdf.cell(58, 5, f"เลขที่: {d['doc_no']}", 0, 1, 'L')
    pdf.set_x(142)
    pdf.cell(58, 5, f"วันที่: {d['doc_date']}", 0, 1, 'L')
    pdf.set_x(142)
    pdf.cell(58, 5, "หน้า 1 / 1", 0, 1, 'L')

    # ชื่อเอกสาร
    pdf.set_y(40)
    pdf.set_font(main_font, 'B', 20)
    pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # 3.4 ข้อมูลลูกค้า (Customer Info)
    pdf.ln(2)
    start_y = pdf.get_y()
    
    # ฝั่งซ้าย
    pdf.set_xy(10, start_y)
    pdf.set_font(main_font, '', 12)
    pdf.multi_cell(110, 6, f"ลูกค้า: {d['c_name']}\nผู้ติดต่อ: {d['contact']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']} แฟกซ์: {d['c_fax']}", 0, 'L')
    
    # ฝั่งขวา (เงื่อนไข)
    pdf.set_xy(130, start_y)
    pdf.multi_cell(70, 6, f"วันที่ส่งของ: {d['due_date']}\nยืนราคา: {d['valid_days']} วัน\nเครดิต: {d['credit']} วัน\nวันหมดอายุ: {d['exp_date']}", 0, 'L')
    
    # ขยับ Cursor ลงมาต่ำสุด
    pdf.set_y(max(pdf.get_y(), start_y + 35))

    # 3.5 ตารางสินค้า (Table)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font(main_font, 'B', 11)
    cols = [15, 80, 20, 15, 25, 15, 25] # ความกว้างคอลัมน์
    headers = ["รหัส", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    
    for i, h in enumerate(headers):
        pdf.cell(cols[i], 8, h, 1, 0, 'C', True)
    pdf.ln()

    # วนลูปรายการสินค้า
    pdf.set_font(main_font, '', 11)
    for idx, row in items_df.iterrows():
        name = str(row['รายการ'])
        if not name or name == "0" or name == "": continue # ข้ามแถวว่าง

        # ดึงค่าและจัด Format
        qty = to_num(row['จำนวน'])
        price = to_num(row['ราคา'])
        disc = to_num(row['ส่วนลด'])
        total = (qty * price) - disc
        
        data = [
            str(row['รหัสสินค้า']),
            name,
            f"{qty:,.2f}",
            str(row['หน่วย']),
            f"{price:,.2f}",
            f"{disc:,.2f}",
            f"{total:,.2f}"
        ]
        
        # วาด Cell
        for i, txt in enumerate(data):
            align = 'L' if i == 1 else 'R' # ชื่อชิดซ้าย ที่เหลือชิดขวา
            if i == 0 or i == 3: align = 'C' # รหัสกับหน่วยกึ่งกลาง
            pdf.cell(cols[i], 7, txt, 1, 0, align)
        pdf.ln()

    # 3.6 สรุปยอดเงิน (Totals)
    pdf.ln(2)
    y_after_table = pdf.get_y()
    
    # หมายเหตุ (ซ้าย)
    pdf.set_xy(10, y_after_table)
    pdf.set_font(main_font, 'B', 12)
    pdf.cell(20, 6, "หมายเหตุ:", 0, 1)
    pdf.set_font(main_font, '', 11)
    pdf.multi_cell(110, 5, remark_text, 0, 'L')

    # ตัวเลข (ขวา)
    x_label = 130
    x_val = 170
    curr_y = y_after_table
    
    def print_summary(label, val, bold=False):
        nonlocal curr_y
        pdf.set_xy(x_label, curr_y)
        pdf.set_font(main_font, 'B' if bold else '', 12)
        pdf.cell(40, 6, label, 0, 0, 'R')
        pdf.set_xy(x_val, curr_y)
        pdf.cell(30, 6, f"{val:,.2f}", 1 if bold else 0, 1, 'R')
        curr_y += 6

    print_summary("รวมเงิน:", summary['gross'])
    print_summary("ส่วนลดรวม:", summary['discount'])
    print_summary("ยอดหลังหักส่วนลด:", summary['subtotal'])
    
    if show_vat:
        print_summary("ภาษีมูลค่าเพิ่ม 7%:", summary['vat'])
    
    print_summary("จำนวนเงินสุทธิ:", summary['grand_total'], True)
    
    # แสดงตัวหนังสือบาท (Text Baht) - ถ้าต้องการฟังก์ชันนี้ต้องเพิ่ม BahtText library (ใส่ตัวอย่างไว้แบบ static ก่อน)
    pdf.set_xy(10, curr_y + 2)
    pdf.set_font(main_font, 'B', 11)
    pdf.cell(100, 6, f"( ราคารวมภาษีมูลค่าเพิ่มแล้ว )", 0, 1, 'L')

    # 3.7 ลายเซ็น (Signatures)
    pdf.set_y(-40) # 4cm จากด้านล่าง
    sig_y = pdf.get_y()
    
    positions = [10, 75, 140]
    titles = ["ผู้สั่งซื้อสินค้า", "พนักงานขาย", "ผู้อนุมัติ"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    
    for i in range(3):
        pdf.set_xy(positions[i], sig_y)
        pdf.cell(50, 5, "..................................", 0, 1, 'C')
        pdf.set_xy(positions[i], sig_y + 5)
        pdf.cell(50, 5, titles[i], 0, 1, 'C')
        pdf.set_xy(positions[i], sig_y + 10)
        pdf.cell(50, 5, f"({names[i]})" if names[i] else "(..................................)", 0, 1, 'C')
        pdf.set_xy(positions[i], sig_y + 15)
        pdf.cell(50, 5, "วันที่ ...../...../..........", 0, 1, 'C')

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
        my_addr = st.text_area("ที่อยู่", "123 ถนนสุขุมวิท แขวงคลองเตย เขตคลองเตย กทม. 10110", height=68, key="my_addr")
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
        # ดึงรายชื่อลูกค้าจาก Session State (ที่โหลดมาจากไฟล์)
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
    
    # แสดงตารางให้แก้ไขได้
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

    # คำนวณยอดเงิน
    calc_df = edited_df.copy()
    calc_df['qty'] = calc_df['จำนวน'].apply(to_num)
    calc_df['price'] = calc_df['ราคา'].apply(to_num)
    calc_df['disc'] = calc_df['ส่วนลด'].apply(to_num)
    calc_df['total'] = (calc_df['qty'] * calc_df['price']) - calc_df['disc']
    
    sum_gross = (calc_df['qty'] * calc_df['price']).sum()
    sum_disc = calc_df['disc'].sum()
    sum_subtotal = calc_df['total'].sum()

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
        
        # ปุ่มสร้าง PDF (ปรับให้ใหญ่เต็มจอสำหรับมือถือ)
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
                    items_df=edited_df,
                    summary={"gross": sum_gross, "discount": sum_disc, "subtotal": sum_subtotal, "vat": vat_amount, "grand_total": grand_total},
                    sigs={"s1": sig_cust, "s2": sig_sale, "s3": sig_mgr},
                    remark_text=remark,
                    show_vat=use_vat
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
    
    # ใช้ Data Editor แก้ไขได้เลย
    edited_cust = st.data_editor(
        st.session_state.db_customers,
        num_rows="dynamic",
        use_container_width=True,
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
            
            # *** หัวใจสำคัญ: รีเฟรชหน้าจอทันที เพื่อให้ Tab 1 เห็นข้อมูลใหม่ ***
            st.rerun()

    with col_btn2:
        if st.button("❌ ยกเลิก / รีโหลดใหม่", use_container_width=True):
            # ล้าง Session เพื่อโหลดใหม่จากไฟล์
            del st.session_state.db_customers
            st.rerun()

# ------------------------------------------------------------------
# TAB 3: ฐานข้อมูลสินค้า (Fix Sync & Mobile)
# ------------------------------------------------------------------
with tab3:
    st.header("จัดการฐานข้อมูลสินค้า")
    
    edited_prod = st.data_editor(
        st.session_state.db_products,
        num_rows="dynamic",
        use_container_width=True,
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
            
            # *** หัวใจสำคัญ: รีเฟรชหน้าจอทันที ***
            st.rerun()

    with col_p2:
        if st.button("❌ รีโหลดสินค้าใหม่", use_container_width=True):
            del st.session_state.db_products
            st.rerun()
