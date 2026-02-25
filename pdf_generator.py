import os
import io
from fpdf import FPDF
from bahttext import bahttext 
from database import to_int

# นำเข้าไลบรารีสำหรับแปลงรูปภาพ (หากไม่ได้ติดตั้ง จะมีการแจ้งเตือนหน้าเว็บ)
try:
    import fitz  # pip install PyMuPDF
    from PIL import Image # pip install Pillow
    HAS_IMG_LIB = True
except ImportError:
    HAS_IMG_LIB = False

FONT_PATH = "THSarabunNew.ttf" 

# ==========================================
# PDF ENGINE (Updated: doc_title support)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line, doc_title="ใบเสนอราคา (QUOTATION)"):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)
    
    # Prepare Font
    if os.path.exists(FONT_PATH):
        pdf.add_font('THSarabun', '', FONT_PATH, uni=True)
        pdf.add_font('THSarabun', 'B', FONT_PATH, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    # --- Prepare Data for Pagination ---
    valid_items = items_df[items_df['รายการ'].str.strip() != ""].copy()
    
    # Constants
    MAX_ROWS_PER_PAGE = 15
    total_items = len(valid_items)
    
    # Calculate pages needed
    import math
    num_pages = math.ceil(total_items / MAX_ROWS_PER_PAGE)
    if num_pages == 0: num_pages = 1
    
    for page in range(num_pages):
        pdf.add_page()
        
        # --- HEADER ---
        for ext in ['png', 'jpg', 'jpeg']:
            if os.path.exists(f"logo.{ext}"):
                pdf.image(f"logo.{ext}", x=15, y=10, w=25)
                break
                
        pdf.set_xy(45, 10)
        pdf.set_font(use_f, 'B', 18)
        pdf.cell(0, 8, f"{d['my_comp']}", 0, 1, 'L')
        
        pdf.set_x(45)
        pdf.set_font(use_f, '', 14)
        pdf.multi_cell(100, 6, f"{d['my_addr']}\nโทร: {d['my_tel']} แฟกซ์: {d['my_fax']}\nเลขผู้เสียภาษี: {d['my_tax']}", 0, 'L')

        # Doc No Box
        pdf.set_xy(140, 10)
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(55, 20, "", 1, 0)
        pdf.set_xy(142, 13)
        pdf.cell(50, 6, f"เลขที่: {d['doc_no']}", 0, 1, 'L')
        pdf.set_x(142)
        pdf.cell(50, 6, f"วันที่: {d['doc_date']}", 0, 1, 'L')
        pdf.set_xy(142, 25)
        pdf.set_font(use_f, '', 12)
        pdf.cell(50, 4, f"หน้า {page+1} / {num_pages}", 0, 1, 'R')

        # Title (Dynamic)
        pdf.set_y(45)
        pdf.set_font(use_f, 'B', 26)
        pdf.cell(0, 10, doc_title, 0, 1, 'C')

        # Customer Info
        pdf.set_y(60)
        start_y = pdf.get_y()
        
        pdf.set_font(use_f, '', 14)
        # ลูกค้า
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(15, 7, "ลูกค้า: ", 0, 0)
        pdf.set_font(use_f, '', 14)
        pdf.cell(0, 7, f"{d['c_name']}", 0, 1)
        
        # ผู้ติดต่อ
        pdf.set_x(15)
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(20, 7, "ผู้ติดต่อ: ", 0, 0)
        pdf.set_font(use_f, '', 14)
        pdf.cell(0, 7, f"{d['contact']}", 0, 1)
        
        # ที่อยู่ / โทร / แฟกซ์
        pdf.set_x(15)
        pdf.multi_cell(110, 6, f"ที่อยู่: {d['c_addr']}\nโทร: {d['c_tel']} แฟกซ์: {d['c_fax']}", 0, 'L')
        
        pdf.set_xy(135, start_y)
        pdf.multi_cell(65, 7, 
            f"กำหนดส่ง: {d['due_date']}\n"
            f"ยืนราคา: {d['valid_days']} วัน\n"
            f"เครดิต: {d['credit']} วัน\n"
            f"ครบกำหนด: {d['exp_date']}", 
            0, 'L')

        # --- TABLE ---
        pdf.set_y(90)
        cols_w = [12, 73, 15, 15, 25, 15, 25] 
        headers = ["ลำดับ", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font(use_f, 'B', 13)
        for i, h in enumerate(headers):
            pdf.cell(cols_w[i], 9, h, 1, 0, 'C', True)
        pdf.ln()

        pdf.set_font(use_f, '', 13)
        row_height = 8 
        
        start_idx = page * MAX_ROWS_PER_PAGE
        end_idx = start_idx + MAX_ROWS_PER_PAGE
        page_items = valid_items.iloc[start_idx:end_idx]
        
        rows_to_print = MAX_ROWS_PER_PAGE 
        
        for i in range(rows_to_print):
            current_item_idx = start_idx + i
            
            if i < len(page_items):
                row = page_items.iloc[i]
                q = to_int(row.get('จำนวน'))
                p = to_int(row.get('ราคา'))
                dis = to_int(row.get('ส่วนลด'))
                total = int(round((q * p) - dis))
                
                vals = [
                    str(current_item_idx + 1),
                    str(row.get('รายการ')),
                    f"{q:,.0f}",
                    str(row.get('หน่วย')),
                    f"{p:,.0f}",
                    f"{dis:,.0f}" if dis > 0 else "-",
                    f"{total:,.0f}"
                ]
            else:
                vals = ["", "", "", "", "", "", ""]
            
            for j, txt in enumerate(vals):
                align = 'C'
                if j == 1: align = 'L'
                pdf.cell(cols_w[j], row_height, txt, 1, 0, align)
            pdf.ln()

        # --- SUMMARY (Only on Last Page) ---
        if page == num_pages - 1:
            pdf.ln(2)
            current_y = pdf.get_y()
            
            # --- ส่วนหมายเหตุ ---
            pdf.set_xy(15, current_y)
            pdf.set_font(use_f, 'B', 14)
            pdf.cell(0, 7, "หมายเหตุ / Remarks:", 0, 1)
            pdf.set_font(use_f, '', 13)
            pdf.multi_cell(90, 5, remark_text, 0, 'L')
            
            # --- ส่วนตัวเลขสรุป ---
            sum_x_label = 130 
            sum_x_val = 170   
            sum_y = current_y
            
            def print_sum_row(label, value, bold=False, line=False):
                nonlocal sum_y
                pdf.set_xy(sum_x_label, sum_y)
                pdf.set_font(use_f, 'B' if bold else '', 13)
                pdf.cell(40, 6, label, 0, 0, 'R')
                pdf.set_xy(sum_x_val, sum_y)
                pdf.cell(25, 6, f"{value:,.0f}", 'B' if line else 0, 1, 'R')
                sum_y += 6

            print_sum_row("รวมเงินสินค้า:", summary['gross'])
            print_sum_row("หักส่วนลด:", summary['discount'])
            print_sum_row("ยอดหลังหักส่วนลด:", summary['subtotal'])
            
            if show_vat_line:
                print_sum_row("ภาษีมูลค่าเพิ่ม 7%:", summary['vat'])
            
            grand_total_val = summary['grand_total']
            baht_text_str = bahttext(grand_total_val)
            
            pdf.set_xy(110, sum_y)
            pdf.set_font(use_f, 'B', 13)
            pdf.cell(40, 6, "ยอดรวมสุทธิ:", 0, 0, 'R')
            
            pdf.set_xy(150, sum_y)
            full_str = f"{grand_total_val:,.2f}  ({baht_text_str})"
            pdf.cell(45, 6, full_str, 0, 1, 'R')

            # --- SIGNATURES ---
            pdf.set_y(-35) 
            pdf.set_font(use_f, '', 13)
            
            sig_labels = ["ผู้สั่งซื้อสินค้า", "พนักงานขาย", "ผู้อนุมัติ"]
            names = [sigs['s1'], sigs['s2'], sigs['s3']]
            x_positions = [20, 85, 150]
            
            y_sig = pdf.get_y()
            
            for i in range(3):
                pdf.set_xy(x_positions[i], y_sig)
                pdf.cell(40, 6, "........................................", 0, 1, 'C')
                pdf.set_xy(x_positions[i], y_sig + 6)
                pdf.cell(40, 6, sig_labels[i], 0, 1, 'C')
                pdf.set_xy(x_positions[i], y_sig + 12)
                disp = f"({names[i]})" if names[i] else "(........................................)"
                pdf.cell(40, 6, disp, 0, 1, 'C')
                pdf.set_xy(x_positions[i], y_sig + 18)
                pdf.cell(40, 6, "วันที่ ...../...../..........", 0, 1, 'C')

    return bytes(pdf.output())

# --- ฟังก์ชันช่วยเหลือสำหรับแปลง PDF เป็นรูปภาพ ---
def convert_pdf_to_image(pdf_bytes, format_type):
    if not HAS_IMG_LIB:
        return None, "กรุณาติดตั้งไลบรารีเพิ่มเติม: pip install PyMuPDF Pillow"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        
        if not images:
            return None, "ไม่สามารถอ่านหน้า PDF ได้"
            
        # นำรูปภาพของแต่ละหน้ามาต่อกันเป็นรูปเดียว (บนลงล่าง)
        widths, heights = zip(*(i.size for i in images))
        max_width = max(widths)
        total_height = sum(heights)
        
        new_im = Image.new('RGB', (max_width, total_height), (255, 255, 255))
        y_offset = 0
        for im in images:
            new_im.paste(im, (0, y_offset))
            y_offset += im.size[1]
            
        img_byte_arr = io.BytesIO()
        pil_format = "JPEG" if format_type.upper() == "JPG" else "PNG"
        new_im.save(img_byte_arr, format=pil_format)
        return img_byte_arr.getvalue(), None
    except Exception as e:
        return None, str(e)