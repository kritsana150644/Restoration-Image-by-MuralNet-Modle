import cv2
import numpy as np
import os

# ============================================================
# Utility: Connected Components Filter
# ============================================================
def _cc_filter(mask, min_area=0, keep_small=True): 
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8) 
    keep = np.zeros_like(mask)

    for i in range(1, num_labels):  # ข้าม background (label 0)
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            keep[labels == i] = 255
        elif keep_small:  # ถ้าเลือกเก็บจุดเล็กด้วย
            keep[labels == i] = 255

    return keep
#ฟังก์ชั่นนี้ทำหน้าที่กรองส่วนที่เล็กๆ ด้วย Connected Components
#แยกแต่ละวัตถุที่เชื่อมกันในmask ออกมา
#num_labals จำนวนวัตถุทั้งหมด รวม background
#labels แผนที่ของ pixel 
#stats เก็บข้อมูลแต่ละวัตถุ

# ============================================================
# Method 1: Threshold-based Masking (เร็วมาก)
# ============================================================
def box_to_mask_threshold(img, box, min_area=40):
    """
    สร้าง mask จากกรอบ (box) ด้วยการแปลงเป็น grayscale แล้วใช้ Otsu Threshold
    เหมาะกับพื้นที่ใหญ่ที่ต้องการความเร็ว
    """
    
    x1, y1, x2, y2 = map(int, box)
    x1, x2 = sorted([x1, x2]); y1, y2 = sorted([y1, y2])
    crop = img[y1:y2, x1:x2] #ตัดภาพพิกัดจากส่วนนั้น
    if crop.size == 0: 
        return np.zeros(img.shape[:2], np.uint8)

    # แปลงเป็น grayscale
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # ใช้ Otsu ตัดค่าauto แล้วตรวจจับหาวัตถุในภาพ แล้วเปลี่ยนภาพให้กลายเป็นภาพขาวดำ
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # ตรวจว่าผลลัพธ์กลับด้านไหม (กรณีพื้นที่สว่างเป็น background)
    if np.mean(gray[thr == 255]) < np.mean(gray[thr == 0]):
        thr = cv2.bitwise_not(thr)

    # กรองจุด noise ออก
    thr = _cc_filter(thr, min_area=min_area)

    # รวม mask กลับไปในขนาดเต็มภาพ
    full = np.zeros(img.shape[:2], np.uint8)
    full[y1:y2, x1:x2] = thr
    return full


# ============================================================
# Method 2: GrabCut-based Masking (ละเอียดแต่ช้ากว่า)
# ============================================================
def box_to_mask_grabcut_full(img, box, iters=2, min_area=40):
    """
    ใช้ GrabCut สำหรับสร้าง mask แบบละเอียด โดยเหมาะกับพื้นที่เล็ก
    ถ้าเกิด error (พื้นที่แคบเกิน) จะ fallback ไปใช้ threshold แทน
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = map(int, box)
    x1, x2 = sorted([max(0, x1), min(w-1, x2)])
    y1, y2 = sorted([max(0, y1), min(h-1, y2)])

    if x2 - x1 < 2 or y2 - y1 < 2:#กว้างสูง น้อยกว่า 2 pixel ไม่ประมวลผล
        return np.zeros((h, w), np.uint8)

    mask = np.zeros((h, w), np.uint8)
    rect = (x1, y1, x2 - x1, y2 - y1) #พิกัดกรอบ
    bgdModel = np.zeros((1, 65), np.float64) #พื้นหลัง
    fgdModel = np.zeros((1, 65), np.float64) #วัตถุ

    try:
        # GrabCut algorithm (iterative refinement)
        cv2.grabCut(img, mask, rect, bgdModel, fgdModel, iters, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        # ถ้า error (เช่น พื้นที่แคบมาก) → ใช้ threshold method แทน
        return box_to_mask_threshold(img, box, min_area=min_area)

    # เก็บเฉพาะ pixel ที่เป็น foreground หรือ foreground ที่ยังไม่แน่ใจ
    out = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # กรอง noise ออก
    out = _cc_filter(out, min_area=min_area)

    # จำกัด mask ให้อยู่ในกรอบที่เลือกเท่านั้น
    roi = np.zeros((h, w), np.uint8)
    roi[y1:y2, x1:x2] = 255
    out = cv2.bitwise_and(out, roi)
    return out


# ============================================================
# Mask Refinement: Feathering edges (เนียนขอบ)
# ============================================================
def soften_and_expand_mask(mask, dilate_size=7, blur_size=11):
    """
    ทำให้ mask ดูนุ่มนวลและครอบคลุมรอยแตกหรือขอบเพิ่มเติม
    - dilate: ขยายขอบออก
    - blur: เบลอขอบเพื่อให้เนียน
    """
    if dilate_size > 0: #ขยายขอบของmask     
        kernel = np.ones((dilate_size, dilate_size), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
    if blur_size > 0: #เบลอขอบ
        mask = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)
        # แปลงกลับเป็น binary (255 / 0)
        mask = (mask > 10).astype(np.uint8) * 255
    return mask


# ============================================================
# Main: Fast Multi-box Auto Mask
# ============================================================
def fast_multi_box_auto_mask(img, boxes):
    """
    ประมวลผลหลายกรอบพร้อมกัน (multi-box)
    โดยจะเลือกวิธีสร้าง mask ตามขนาดของกรอบ:
    - พื้นที่ใหญ่ → ใช้วิธี Threshold (เร็ว)
    - พื้นที่เล็ก → ใช้ GrabCut (ละเอียด)
    สุดท้ายรวมผลลัพธ์ทั้งหมดเป็น mask เดียว
    """
    h, w = img.shape[:2]
    final_mask = np.zeros((h, w), np.uint8)

    for (x1, y1, x2, y2) in boxes:
        area = abs((x2 - x1) * (y2 - y1))

        # เลือกวิธีตามขนาดกรอบ
        if area > 150 * 150:   # ถ้าพื้นที่ใหญ่ → ใช้ threshold (เร็วกว่า)
            local = box_to_mask_threshold(img, (x1, y1, x2, y2), min_area=10)
        else:                  # ถ้าพื้นที่เล็ก → ใช้ grabcut (แม่นกว่า)
            local = box_to_mask_grabcut_full(img, (x1, y1, x2, y2), iters=2, min_area=5)

        # รวม mask ของแต่ละกล่องเข้าด้วยกัน
        final_mask = cv2.bitwise_or(final_mask, local)

    # ปรับขอบ mask ให้เนียน
    final_mask = soften_and_expand_mask(final_mask, dilate_size=7, blur_size=11)
    return final_mask


# alias (ให้เรียกชื่อเดิม multi_box_auto_mask ได้)
multi_box_auto_mask = fast_multi_box_auto_mask
