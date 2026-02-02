import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

# ==========================================
# 1. INITIAL CONFIG & SESSION STATE
# ==========================================
st.set_page_config(page_title="SIWAKIT Enterprise System", layout="wide")

# จำลองฐานข้อมูล (Mock Database) ถ้ายังไม่มีให้สร้างขึ้นมา
if "db_customers" not in st.session_state:
    st.session_state.db_customers = pd.DataFrame([
        {"รหัส": "C001", "ชื่อบริษัท": "บริษัท ตัวอย่าง จำกัด", "ผู้ติดต่อ": "คุณสมชาย", "ที่อยู่": "123 กทม.", "โทร": "081-111-1111", "แฟกซ์": "02-222-2222"},
        {"รหัส": "C002", "ชื่อบริษัท": "หจก. ทดสอบระบบ", "ผู้ติดต่อ": "คุณสมหญิง", "ที่อยู่": "456 เชียงใหม่", "โทร": "089-999-9999", "แฟกซ์": "-"}
    ])

if "db_products" not in st.session_state:
    st.session_state.db_products = pd.DataFrame([
        {"รหัสสินค้า": "P001", "รายการ": "สินค้าตัวอย่าง A", "ราคา": 1500, "หน่วย": "ชิ้น"},
        {"รหัสสินค้า": "P002", "รายการ": "สินค้าตัวอย่าง B", "ราคา": 2500, "หน่วย": "เครื่อง"},
        {"รหัสสินค้า": "P003", "รายการ": "ค่าบริการติดตั้ง", "ราคา": 5000, "หน่วย": "งาน"}
    ])

def to_num(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val else 0.0
    except: return 0.0

# ==========================================
# 2. PDF ENGINE
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    font_path = "THSarabunNew.ttf"
    use_f = 'THSarabun' if os.path.exists(font_path) else 'Arial'
    if use_f == 'THSarabun':
        pdf.add_font('THSarabun', '', font_path); pdf.add_font('THSarabun', 'B', font_path)

    # --- HEADER ---
    for ext in ['png', 'jpg', 'jpeg']:
        if os.path.exists(f"logo.{ext}"):
            pdf.image(f"logo.{ext}", x=10, y=10, w=22)
            break
            
    pdf.set_xy(35, 10); pdf.set_font(use_f, 'B', 14)
    pdf.multi_cell(100, 6, f"บริษัท: {d['my_comp']}\nที่อยู่: {d['my_addr']}\nโทร: {d['my_tel']} โทรสาร: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

    pdf.set_xy(145, 10); pdf.set_font(use_f, 'B', 12)
    pdf.cell(55, 16, "", 1, 0)
    pdf.set_xy(146, 12)
    pdf.multi_cell(53, 6, f"เลขที่: {d['doc_no']}\nวันที่: {d['doc_date']}", 0, 'L')

    pdf.set_y(42); pdf.set_font(use_f, 'B', 24); pdf.cell(0, 10, "ใบเสนอราคา (QUOTATION)", 0, 1, 'C')

    # --- INFO ---
    pdf.set_font(use_f, '', 14); pdf.ln(2); start_y = pdf.get_y()
    pdf.set_xy(10, start_y)
    pdf.multi_cell(115, 6, f"ชื่อผู้ติดต่อ: {d['contact']}\nบริษัท: {d['c_name']}\nที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']}  โทรสาร: {d['c_fax']}")
    y_left = pdf.get_y()
    pdf.set_xy(130, start_y)
    pdf.multi_cell(75, 6, f"วันที่กำหนดส่ง: {d['due_date']}\nยืนราคา (วัน): {d['valid_days']}  Expire Date: {d['exp_date']}\nเครดิต (วัน): {d['credit']}", 0, 'L')
    y_right = pdf.get_y()
    pdf.set_y(max(y_left, y_right) + 5)

    # --- TABLE ---
    pdf.set_fill_color(240, 240, 240); pdf.set_font(use_f, 'B', 11)
    w = [15, 75, 15, 15, 25, 15, 30]
    headers = ["รหัสสินค้า", "รายการ", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
    for i in range(len(headers)): pdf.cell(w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln(); pdf.set_font(use_f, '', 11)
    row_height = 6.0
    for i in range(20):
        if i < len(items_df):
            row = items_df.iloc[i]
            if str(row.get('รายการ','')).strip() != "":
                val = [str(row.get('รหัสสินค้า','')), str(row.get('รายการ','')), f"{to_num(row.get('จำนวน')):,.0f}", 
                       str(row.get('หน่วย','')), f"{to_num(row.get('ราคา')):,.0f}", f"{to_num(row.get('ส่วนลด')):,.0f}", f"{to_num(row.get('รวมเงิน',0)):,.0f}"]
            else: val = [""]*7
        else: val = [""]*7
        for j in range(7):
            align = 'L' if j == 1 else 'C'
            if j == 6: align = 'R'
            pdf.cell(w[j], row_height, val[j], 1, 0, align)
        pdf.ln()

    # --- FOOTER ---
    pdf.ln(2); footer_start_y = pdf.get_y()
    
    # หมายเหตุ
    pdf.set_xy(10, footer_start_y)
    pdf.set_font(use_f, 'B', 12); pdf.cell(20, 6, "หมายเหตุ:", 0, 1, 'L')
    pdf.set_font(use_f, '', 12); pdf.set_x(10); pdf.multi_cell(105, 5, remark_text, 0, 'L')
    
    # ยอดเงิน
    labels_x = 125; values_x = 175; sum_line_h = 5.5; curr_sum_y = footer_start_y 

    def add_sum_row(label, value, is_bold=False, is_red=False):
        nonlocal curr_sum_y
        pdf.set_font(use_f, 'B' if is_bold else '', 13 if is_bold else 12)
        if is_red: pdf.set_text_color(180, 0, 0)
        else: pdf.set_text_color(0, 0, 0)
        pdf.set_xy(labels_x, curr_sum_y); pdf.cell(45, sum_line_h, label, 0, 0, 'R')
        pdf.set_xy(values_x, curr_sum_y); pdf.cell(25, sum_line_h, f"{value:,.2f}", 'B', 1, 'R')
        curr_sum_y += sum_line_h

    add_sum_row("รวมเงินย่อย (Gross Total):", summary['gross'])
    add_sum_row("ส่วนลด (Total Discount):", summary['discount'])
    add_sum_row("หลังหักส่วนลด (Sub Total):", summary['subtotal'])
    
    # *** จุดสำคัญ: ถ้าไม่เอา VAT ไม่ต้องโชว์บรรทัดนี้เลย ***
    if show_vat_line:
        add_sum_row("ภาษีมูลค่าเพิ่ม (VAT 7%):", summary['vat'])
        
    add_sum_row("ยอดรวมทั้งสิ้น (Grand Total):", summary['grand_total'], True, True)

    # ลายเซ็น
    pdf.set_y(-35); pdf.set_text_color(0, 0, 0); pdf.set_font(use_f, '', 11)
    titles = ["ผู้อนุมัติซื้อ (ลูกค้า)", "พนักงานขาย", "ผู้จัดการฝ่ายขาย"]
    names = [sigs['s1'], sigs['s2'], sigs['s3']]
    pos_x = [10, 75, 140]; y_sig = pdf.get_y()
    for i in range(3):
        pdf.set_xy(pos_x[i], y_sig); pdf.cell(60, 5, "...................................................", 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_sig + 5); pdf.cell(60, 5, titles[i], 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_sig + 10); pdf.cell(60, 5, f"({names[i]})" if names[i] else "(...................................................)", 0, 1, 'C')
        pdf.set_xy(pos_x[i], y_sig + 15); pdf.cell(60, 5, "วันที่: ......../......../........", 0, 1, 'C')

    return bytes(pdf.output())

# ==========================================
# 3. UI - TAB SYSTEM
# ==========================================
st.title("🚀 SIWAKIT Enterprise Quotation System")

tab1, tab2, tab3 = st.tabs(["📝 สร้างใบเสนอราคา", "👥 ฐานข้อมูลลูกค้า", "📦 คลังสินค้า"])

# --- TAB 1: ใบเสนอราคา ---
with tab1:
    # 1.1 Header
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 ข้อมูลผู้เสนอราคา")
        my_comp = st.text_input("ชื่อบริษัท", "SIWAKIT")
        my_addr = st.text_input("ที่อยู่บริษัท", "123 ...")
        my_tel = st.text_input("โทรศัพท์", "02-xxx-xxxx")
        my_fax = st.text_input("โทรสาร (Fax)", "-")
        my_tax = st.text_input("เลขผู้เสียภาษี", "1234567890123")
    with c2:
        st.subheader("📄 รายละเอียดเอกสาร")
        doc_no = st.text_input("เลขที่ใบเสนอราคา", f"QT-{datetime.now().strftime('%y%m%d-%H')}")
        doc_date = st.text_input("วันที่ออกเอกสาร", datetime.now().strftime('%d/%m/%Y'))
        due_date = st.text_input("วันที่กำหนดส่ง", "7 วัน")
        col_v1, col_v2 = st.columns(2)
        valid_days = col_v1.text_input("ยืนราคา (วัน)", "30")
        exp_date = col_v2.text_input("Expire Date", datetime.now().strftime('%d/%m/%Y'))
        credit = st.text_input("เครดิต (วัน)", "30")

    st.divider()

    # 1.2 Customer (เพิ่มระบบดึงข้อมูลจาก Tab 2)
    c_col_h1, c_col_h2 = st.columns([1, 1])
    with c_col_h1: st.subheader("👤 ข้อมูลลูกค้า")
    with c_col_h2: 
        # Dropdown เลือกลูกค้า
        cust_options = ["-- พิมพ์เอง --"] + st.session_state.db_customers['ชื่อบริษัท'].tolist()
        selected_cust = st.selectbox("📥 เลือกลูกค้าเก่า (เพื่อเติมข้อมูลอัตโนมัติ)", cust_options)

    # Logic การเติมข้อมูลลูกค้า
    default_c_name = ""
    default_contact = ""
    default_c_addr = ""
    default_c_tel = ""
    default_c_fax = ""
    
    if selected_cust != "-- พิมพ์เอง --":
        cust_row = st.session_state.db_customers[st.session_state.db_customers['ชื่อบริษัท'] == selected_cust].iloc[0]
        default_c_name = cust_row['ชื่อบริษัท']
        default_contact = cust_row['ผู้ติดต่อ']
        default_c_addr = cust_row['ที่อยู่']
        default_c_tel = cust_row['โทร']
        default_c_fax = cust_row['แฟกซ์']

    c3, c4 = st.columns(2)
    with c3:
        # ใช้ value=... เพื่อเติมค่า (ถ้ามีการเลือก)
        c_name = st.text_input("ชื่อบริษัทลูกค้า", value=default_c_name)
        contact = st.text_input("ชื่อผู้ติดต่อ", value=default_contact)
        c_addr = st.text_area("ที่อยู่จัดส่ง/วางบิล", value=default_c_addr, height=70)
    with c4:
        st.write("<br><br>", unsafe_allow_html=True)
        c_tel = st.text_input("เบอร์โทรศัพท์ลูกค้า", value=default_c_tel)
        c_fax = st.text_input("เบอร์แฟกซ์ลูกค้า", value=default_c_fax)

    # 1.3 Table (เพิ่มระบบดึงข้อมูลจาก Tab 3)
    st.subheader("📦 รายการสินค้า")
    
    # เตรียม Dataframe เริ่มต้น
    if "grid_df" not in st.session_state:
        st.session_state.grid_df = pd.DataFrame([{"รหัสสินค้า": "", "รายการ": "", "จำนวน": 0, "หน่วย": "", "ราคา": 0, "ส่วนลด": 0}] * 20)

    # ใช้ Column Config ให้เลือกสินค้าได้
    product_codes = st.session_state.db_products['รหัสสินค้า'].tolist()
    
    edited_grid = st.data_editor(
        st.session_state.grid_df,
        column_config={
            "รหัสสินค้า": st.column_config.SelectboxColumn(
                "รหัสสินค้า",
                help="เลือกจากฐานข้อมูลสินค้า",
                width="small",
                options=product_codes,
                required=False
            )
        },
        num_rows="dynamic",
        use_container_width=True,
        key="data_editor_grid"
    )

    # Logic: Sync ข้อมูลสินค้า (ถ้ารหัสเปลี่ยน ให้ดึงชื่อ/ราคา/หน่วยมาใส่)
    # เราต้อง Loop เช็คว่า User เลือก Code มาหรือเปล่า
    updated_df = edited_grid.copy()
    for idx, row in updated_df.iterrows():
        code = row['รหัสสินค้า']
        # ถ้ามีรหัส แต่รายการว่าง หรือราคาเป็น 0 (สมมติว่าเพิ่งเลือก) -> ให้ดึงข้อมูลมาใส่
        if code in product_codes:
            # ดึงข้อมูลจาก DB
            prod_info = st.session_state.db_products[st.session_state.db_products['รหัสสินค้า'] == code].iloc[0]
            
            # ถ้าช่องรายการยังว่าง หรือเป็นค่าเดิม ให้เติมชื่อสินค้า
            if not row['รายการ']: 
                updated_df.at[idx, 'รายการ'] = prod_info['รายการ']
            # ถ้าหน่วยว่าง
            if not row['หน่วย']:
                updated_df.at[idx, 'หน่วย'] = prod_info['หน่วย']
            # ถ้าราคาเป็น 0
            if row['ราคา'] == 0:
                updated_df.at[idx, 'ราคา'] = prod_info['ราคา']

    # อัปเดตกลับไปที่ session state เพื่อให้แสดงผลรอบหน้า
    st.session_state.grid_df = updated_df

    # 1.4 Calculation
    df_calc = updated_df.copy()
    df_calc['qty_n'] = df_calc['จำนวน'].apply(to_num)
    df_calc['pri_n'] = df_calc['ราคา'].apply(to_num)
    df_calc['dis_n'] = df_calc['ส่วนลด'].apply(to_num)
    df_calc['รวมเงิน'] = (df_calc['qty_n'] * df_calc['pri_n']) - df_calc['dis_n']
    
    gross_total = (df_calc['qty_n'] * df_calc['pri_n']).sum()
    total_discount = df_calc['dis_n'].sum()
    subtotal = df_calc['รวมเงิน'].sum()

    # 1.5 Footer & VAT Logic
    cf1, cf2 = st.columns([2, 1])
    with cf1:
        remark = st.text_area("📝 หมายเหตุ (Remark)", value="1. สินค้ารับประกัน 1 ปี\n2. กำหนดยืนราคาตามที่ระบุในเอกสาร")
    with cf2:
        st.write("### สรุปยอดเงิน")
        # Checkbox VAT
        use_vat = st.checkbox("✅ คำนวณ VAT 7%", value=True)
        
        if use_vat:
            # *** จุดแก้ไข: ตัดทศนิยมออก (int) ตามสั่ง ***
            vat = int(subtotal * 0.07) 
        else:
            vat = 0.0

        grand_total = subtotal + vat

        st.write(f"รวมเป็นเงิน: {gross_total:,.2f}")
        st.write(f"ส่วนลดทั้งหมด: -{total_discount:,.2f}")
        st.write(f"ยอดหลังหักส่วนลด: {subtotal:,.2f}")
        
        if use_vat:
            st.write(f"ภาษีมูลค่าเพิ่ม 7%: {vat:,.2f}") # แสดงค่าที่ตัดทศนิยมแล้ว
        else:
            st.write("ภาษีมูลค่าเพิ่ม 7%: - (ไม่คิดภาษี)")

        st.metric("ยอดรวมทั้งสิ้น", f"{grand_total:,.2f} บาท")

    # 1.6 Signatures
    sc1, sc2, sc3 = st.columns(3)
    sig1 = sc1.text_input("ชื่อผู้อนุมัติซื้อ (ลูกค้า)")
    sig2 = sc2.text_input("ชื่อพนักงานขาย")
    sig3 = sc3.text_input("ชื่อผู้จัดการฝ่ายขาย")

    # 1.7 Button
    if st.button("🚀 สร้างเอกสาร PDF (เวอร์ชันสมบูรณ์)", type="primary", use_container_width=True):
        doc_data = {
            "my_comp": my_comp, "my_addr": my_addr, "my_tel": my_tel, "my_fax": my_fax, "my_tax": my_tax,
            "doc_no": doc_no, "doc_date": doc_date, "due_date": due_date, "valid_days": valid_days, 
            "exp_date": exp_date, "credit": credit, "c_name": c_name, "contact": contact, 
            "c_addr": c_addr, "c_tel": c_tel, "c_fax": c_fax
        }
        
        pdf_res = create_pdf(
            doc_data, df_calc, 
            {"gross": gross_total, "discount": total_discount, "subtotal": subtotal, "vat": vat, "grand_total": grand_total}, 
            {"s1": sig1, "s2": sig2, "s3": sig3}, 
            remark,
            use_vat # ส่งค่า boolean ไปบอก PDF Engine ว่าจะโชว์บรรทัด VAT ไหม
        )
        
        st.success("✅ สร้างไฟล์ PDF เรียบร้อยแล้ว!")
        st.download_button("📥 ดาวน์โหลดใบเสนอราคา", pdf_res, f"{doc_no}.pdf", "application/pdf")

# --- TAB 2: ฐานข้อมูลลูกค้า (ใช้งานได้จริง) ---
with tab2:
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    st.info("💡 เพิ่ม/ลบ/แก้ไข ข้อมูลตรงนี้ แล้วกลับไปหน้าแรก ข้อมูลจะไปโผล่ในช่องเลือก 'ลูกค้าเก่า' ทันที")
    
    # Editor สำหรับลูกค้า
    edited_customers = st.data_editor(
        st.session_state.db_customers, 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_cust"
    )
    # Save กลับเข้า session state ทันทีที่มีการแก้
    st.session_state.db_customers = edited_customers

# --- TAB 3: ฐานข้อมูลสินค้า (ใช้งานได้จริง) ---
with tab3:
    st.header("📦 จัดการฐานข้อมูลสินค้า")
    st.info("💡 เพิ่ม/ลบ/แก้ไข ข้อมูลตรงนี้ แล้วกลับไปหน้าแรก ในตารางสินค้าจะมีให้เลือก 'รหัสสินค้า' ตามนี้")
    
    # Editor สำหรับสินค้า
    edited_products = st.data_editor(
        st.session_state.db_products, 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_prod"
    )
    # Save กลับเข้า session state
    st.session_state.db_products = edited_products
