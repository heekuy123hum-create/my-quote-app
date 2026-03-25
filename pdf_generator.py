import os
import io
import tempfile
import math
from fpdf import FPDF
from bahttext import bahttext 
from database import to_int

try:
    import fitz 
    from PIL import Image 
    HAS_IMG_LIB = True
except ImportError:
    HAS_IMG_LIB = False

FONT_PATH = "THSarabunNew.ttf" 

def to_f(val):
    try:
        if isinstance(val, str): val = val.replace(',', '')
        return float(val) if val is not None else 0.0
    except:
        return 0.0

# ==========================================
# PDF ENGINE (FIX: กันชนลายเซ็น + summary ไม่ชน)
# ==========================================
def create_pdf(d, items_df, summary, sigs, remark_text, show_vat_line, doc_title="ใบเสนอราคา (QUOTATION)"):
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=False)
    
    if os.path.exists(FONT_PATH):
        pdf.add_font('THSarabun', '', FONT_PATH, uni=True)
        pdf.add_font('THSarabun', 'B', FONT_PATH, uni=True)
        use_f = 'THSarabun'
    else:
        use_f = 'Arial'

    valid_items = items_df[items_df['รายการ'].str.strip() != ""].copy()
    
    MAX_ROWS_PER_PAGE = 15
    total_items = len(valid_items)
    
    num_pages = math.ceil(total_items / MAX_ROWS_PER_PAGE)
    if num_pages == 0: num_pages = 1
    
    for page in range(num_pages):
        pdf.add_page()
        
        if os.path.exists("logo11.jpg"):
            pdf.image("logo11.jpg", x=15, y=10, w=25)
                
        pdf.set_xy(45, 10)
        pdf.set_font(use_f, 'B', 18)
        pdf.cell(0, 8, f"{d.get('my_comp', '')}", 0, 1, 'L')
        
        pdf.set_x(45)
        pdf.set_font(use_f, '', 14)
        pdf.multi_cell(100, 6, f"{d.get('my_addr', '')}\nโทร: {d.get('my_tel', '')}\nเลขผู้เสียภาษี: {d.get('my_tax', '')}", 0, 'L')

        pdf.set_xy(140, 10)
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(55, 20, "", 1, 0)
        pdf.set_xy(142, 13)
        pdf.cell(50, 6, f"เลขที่: {d.get('doc_no', '')}", 0, 1, 'L')
        pdf.set_x(142)
        pdf.cell(50, 6, f"วันที่: {d.get('doc_date', '')}", 0, 1, 'L')
        pdf.set_xy(142, 25)
        pdf.set_font(use_f, '', 12)
        pdf.cell(50, 4, f"หน้า {page+1} / {num_pages}", 0, 1, 'R')

        pdf.set_y(45)
        pdf.set_font(use_f, 'B', 26)
        pdf.cell(0, 10, doc_title, 0, 1, 'C')

        pdf.set_y(60)
        start_y = pdf.get_y()
        
        pdf.set_font(use_f, '', 14)
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(15, 7, "ลูกค้า: ", 0, 0)
        pdf.set_font(use_f, '', 14)
        pdf.cell(0, 7, f"{d.get('c_name', '')}", 0, 1)
        
        pdf.set_x(15)
        pdf.set_font(use_f, 'B', 14)
        pdf.cell(20, 7, "ผู้ติดต่อ: ", 0, 0)
        pdf.set_font(use_f, '', 14)
        pdf.cell(0, 7, f"{d.get('contact', '')}", 0, 1)
        
        pdf.set_x(15)
        pdf.multi_cell(110, 6, f"ที่อยู่: {d.get('c_addr', '')}\nโทร: {d.get('c_tel', '')}", 0, 'L')
        
        pdf.set_xy(135, start_y)
        pdf.multi_cell(65, 7, 
            f"กำหนดส่ง: {d.get('due_date', '')}\n"
            f"ยืนราคา: {d.get('valid_days', '')} วัน\n"
            f"ครบกำหนด: {d.get('exp_date', '')}", 
            0, 'L')

        # --- TABLE ---
        pdf.set_y(90)
        cols_w = [12, 73, 15, 15, 25, 15, 25] 
        headers = ["ลำดับ", "รายการสินค้า", "จำนวน", "หน่วย", "ราคา/หน่วย", "ส่วนลด", "จำนวนเงิน"]
        
        def draw_table_header():
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font(use_f, 'B', 13)
            for i, h in enumerate(headers):
                pdf.cell(cols_w[i], 9, h, 1, 0, 'C', True)
            pdf.ln()
            pdf.set_font(use_f, '', 13)

        draw_table_header()

        row_height = 8 
        
        start_idx = page * MAX_ROWS_PER_PAGE
        end_idx = start_idx + MAX_ROWS_PER_PAGE
        page_items = valid_items.iloc[start_idx:end_idx]
        
        for i in range(MAX_ROWS_PER_PAGE):
            current_item_idx = start_idx + i

            if i < len(page_items):
                row = page_items.iloc[i]
                q = to_f(row.get('จำนวน'))
                p = to_f(row.get('ราคา'))
                dis = to_f(row.get('ส่วนลด'))
                total = round((q * p) - dis, 2)
                
                vals = [
                    str(current_item_idx + 1),
                    str(row.get('รายการ')),
                    f"{q:,.2f}",
                    str(row.get('หน่วย')),
                    f"{p:,.2f}",
                    f"{dis:,.2f}" if dis > 0 else "-",
                    f"{total:,.2f}"
                ]
                
                max_lines = 1
                for j, txt in enumerate(vals):
                    w = pdf.get_string_width(txt)
                    if w > 0:
                        lines = math.ceil(w / (cols_w[j] - 2))
                        if lines > max_lines: max_lines = lines
                
                h = 7 * max_lines 
                if h < 8: h = 8
                
                x = pdf.get_x()
                y = pdf.get_y()

                # ⭐ กันชนลายเซ็น
                if y + h > 250:
                    pdf.add_page()
                    pdf.set_y(90)
                    draw_table_header()
                    x = pdf.get_x()
                    y = pdf.get_y()

                for j, txt in enumerate(vals):
                    align = 'C' if j != 1 else 'L'
                    
                    pdf.rect(x, y, cols_w[j], h)
                    pdf.set_xy(x, y + (h - 7)/2 if max_lines == 1 else y) 
                    pdf.multi_cell(cols_w[j], 7 if max_lines > 1 else h, txt, 0, align)
                    
                    x += cols_w[j]
                
                pdf.set_xy(15, y + h)

            else:
                vals = ["", "", "", "", "", "", ""]
                for j, txt in enumerate(vals):
                    pdf.cell(cols_w[j], row_height, txt, 1, 0, 'C')
                pdf.ln()

        # =========================
        # ⭐ FIX ใหญ่: SUMMARY ไม่ชนลายเซ็น
        # =========================
        if page == num_pages - 1:

            # ประเมินความสูงคร่าวๆ
            estimated_height = 60

            if pdf.get_y() + estimated_height > 250:
                pdf.add_page()

            pdf.ln(2)
            current_y = pdf.get_y()
            
            pdf.set_xy(15, current_y)
            pdf.set_font(use_f, 'B', 14)
            pdf.cell(0, 7, "หมายเหตุ / Remarks:", 0, 1)
            pdf.set_font(use_f, '', 13)
            pdf.multi_cell(90, 5, remark_text, 0, 'L')
            
            sum_x_label = 130 
            sum_x_val = 170   
            sum_y = current_y
            
            def print_sum_row(label, value, bold=False, line=False):
                nonlocal sum_y
                pdf.set_xy(sum_x_label, sum_y)
                pdf.set_font(use_f, 'B' if bold else '', 13)
                pdf.cell(40, 6, label, 0, 0, 'R')
                pdf.set_xy(sum_x_val, sum_y)
                pdf.cell(25, 6, f"{value:,.2f}", 'B' if line else 0, 1, 'R')
                sum_y += 6

            print_sum_row("รวมเงินสินค้า:", summary['gross'])
            print_sum_row("หักส่วนลด:", summary['discount'])
            print_sum_row("ยอดหลังหักส่วนลด:", summary['subtotal'])
            
            if show_vat_line:
                print_sum_row("ภาษีมูลค่าเพิ่ม 7%:", summary['vat'])
            
            grand_total_val = summary['grand_total']
            baht_text_str = bahttext(grand_total_val)
            
            pdf.set_xy(15, sum_y)
            pdf.set_font(use_f, 'B', 13)
            pdf.cell(115, 6, f"({baht_text_str})", 0, 0, 'C')
            
            pdf.set_xy(130, sum_y)
            pdf.cell(40, 6, "ยอดรวมสุทธิ:", 0, 0, 'R')
            
            pdf.set_xy(170, sum_y)
            pdf.cell(25, 6, f"{grand_total_val:,.2f}", 0, 1, 'R')

            # --- SIGNATURE (FIX + รองรับ 547.png) ---
            pdf.set_y(-42) 
            pdf.set_font(use_f, '', 13)
            
            sig_labels = ["ผู้จัดทำ", "ผู้อนุมัติ"]
            names = [sigs.get('s1', ''), sigs.get('s2', '')]
            images = [sigs.get('img1'), sigs.get('img2')]

            # ⭐ ใส่ 547.png ถ้ามี
            if os.path.exists("547.png"):
                images[1] = "547.png"
            
            x_positions = [40, 130]
            y_sig = pdf.get_y()
            
            for i in range(2):
                if images[i]:
                    try:
                        if isinstance(images[i], str):
                            pdf.image(images[i], x=x_positions[i] + 5, y=y_sig - 12, w=30, h=12)
                        elif hasattr(images[i], 'read'):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                tmp.write(images[i].getvalue())
                                tmp_path = tmp.name
                            pdf.image(tmp_path, x=x_positions[i] + 5, y=y_sig - 12, w=30, h=12)
                            os.remove(tmp_path)
                    except:
                        pass

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


# ==========================================
# convert (เหมือนเดิม ไม่แตะ)
# ==========================================
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
        
        if not images: return None, "ไม่สามารถอ่านหน้า PDF ได้"
            
        widths, heights = zip(*(i.size for i in images))
        new_im = Image.new('RGB', (max(widths), sum(heights)), (255, 255, 255))
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
