# ============================================================
#  Thai Mural Restoration System - Flask Backend
#  🟡 Function: รับภาพจากเว็บ → สร้าง mask, edge map → split patch →
#  รันโมเดล inpainting → รวมภาพกลับ → ส่งผลลัพธ์กลับเป็น base64
# ============================================================

import os, io, base64, shutil, sys, time
from flask import Flask, request, jsonify, send_from_directory
from PIL import Image
import numpy as np
import cv2
import shutil
from auto_mask import multi_box_auto_mask   # ✅ โมดูลสร้าง mask อัตโนมัติจากกล่อง (bounding box)
from test import run_inference              # ✅ ฟังก์ชันรันโมเดล inpainting (แทน subprocess)

# ---------- ตั้งค่า Flask ----------
app = Flask(__name__, static_folder="static", static_url_path="")

# ---------- โฟลเดอร์เก็บไฟล์ ----------
SAVE_DIR = "runtime"           # โฟลเดอร์ชั่วคราวสำหรับเก็บไฟล์ระหว่างประมวลผล
MODEL_TEST_DIR = "checkpoints/test"  # โฟลเดอร์ที่โมเดลจะใช้ทดสอบ input/output
os.makedirs(SAVE_DIR, exist_ok=True)

# ---------- ตัวแปรสถานะ Progress ----------
progress_status = {"progress": 0, "message": "idle"}

def set_progress(value, message=""):
    """ตั้งค่าความคืบหน้าการประมวลผล"""
    progress_status["progress"] = int(value)
    progress_status["message"] = message

def reset_progress():
    """รีเซ็ต progress หลังทำงานเสร็จ"""
    progress_status["progress"] = 0
    progress_status["message"] = "idle"

@app.route("/status", methods=["GET"])
def status():
    """ส่งสถานะ progress กลับให้ฝั่งเว็บเพื่อติดตามการทำงาน"""
    return jsonify(progress_status)


# ============================================================
#  🔹 ส่วน Utilities (ฟังก์ชันช่วยเหลือ)
# ============================================================

def dataurl_to_pil(data_url: str) -> Image.Image:
    """แปลง base64 DataURL จากหน้าเว็บให้เป็นภาพ PIL"""
    header, encoded = data_url.split(",", 1)
    raw = base64.b64decode(encoded)
    return Image.open(io.BytesIO(raw))

def create_edge_map(img_np):
    """สร้าง edge map ด้วย Canny edge detection"""
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_white = np.zeros_like(edges)
    edge_white[edges > 0] = 255     # พื้นหลังขาว เส้นขอบดำ
    return edge_white

def save_patches_triplet(img_np, mask_np, edge_np,
                         dir_img, dir_mask, dir_edge,
                         prefix="patch", size=512, stride=256):
    """
    🔸 แบ่งภาพออกเป็น patch ย่อย (512x512) สำหรับการประมวลผล
    - บันทึกภาพต้นฉบับ, mask และ edge เป็นชุด
    - stride = ระยะเลื่อน patch (256 พิกเซล)
    """
    h, w = img_np.shape[:2]
    os.makedirs(dir_img, exist_ok=True)
    os.makedirs(dir_mask, exist_ok=True)
    os.makedirs(dir_edge, exist_ok=True)
    count = 0

    for y in range(0, h, stride):
        for x in range(0, w, stride):
            img_patch  = img_np[y:y+size, x:x+size]
            mask_patch = mask_np[y:y+size, x:x+size]
            edge_patch = edge_np[y:y+size, x:x+size]

            # ถ้า patch ขนาดไม่ครบ 512x512 → เติมขอบ (padding)
            ph, pw = img_patch.shape[:2]
            if ph < size or pw < size:
                padded_img  = np.zeros((size, size, 3), dtype=img_np.dtype)
                padded_mask = np.zeros((size, size), dtype=mask_np.dtype)
                padded_edge = np.zeros((size, size), dtype=edge_np.dtype)
                padded_img[:ph, :pw]  = img_patch
                padded_mask[:ph, :pw] = mask_patch
                padded_edge[:ph, :pw] = edge_patch
                img_patch, mask_patch, edge_patch = padded_img, padded_mask, padded_edge

            # บันทึก patch แต่ละชุด
            cv2.imwrite(os.path.join(dir_img,  f"{prefix}_{count+1:03d}.png"), img_patch)
            cv2.imwrite(os.path.join(dir_mask, f"{prefix}_{count+1:03d}.png"), mask_patch)
            cv2.imwrite(os.path.join(dir_edge, f"{prefix}_{count+1:03d}.png"), edge_patch)
            count += 1

    return count, (h, w)

def reassemble_patches_with_blending(patch_dir, full_size, size=512, stride=256):
    """
    🔸 รวม patch ที่ประมวลผลแล้วกลับมาเป็นภาพใหญ่
    - ใช้การเฉลี่ยน้ำหนัก (blending) เพื่อลบรอยต่อระหว่าง patch
    """
    h, w = full_size
    canvas = np.zeros((h, w, 3), dtype=np.float32)
    weight = np.zeros((h, w, 3), dtype=np.float32)

    patch_files = sorted(os.listdir(patch_dir))
    idx = 0

    for y in range(0, h, stride):
        for x in range(0, w, stride):
            if idx >= len(patch_files):
                break
            patch = cv2.imread(os.path.join(patch_dir, patch_files[idx]))
            if patch is None:
                idx += 1
                continue
            ph, pw = patch.shape[:2]
            patch = patch[:min(ph, h-y), :min(pw, w-x)]
            canvas[y:y+patch.shape[0], x:x+patch.shape[1]] += patch.astype(np.float32)
            weight[y:y+patch.shape[0], x:x+patch.shape[1]] += 1.0
            idx += 1

    weight[weight == 0] = 1
    merged = (canvas / weight).astype(np.uint8)
    return merged

def clear_and_copy(src_dir, dst_dir):
    """
    🔸 ลบโฟลเดอร์ปลายทางเก่า แล้วคัดลอกไฟล์จาก src → dst
    ใช้ก่อนรันโมเดล เพื่อเคลียร์ input เดิมออก
    """
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(dst_dir, exist_ok=True)
    for f in os.listdir(src_dir):
        shutil.copy(os.path.join(src_dir, f), dst_dir)


# ============================================================
#  🔹 ส่วน Routes (API หลัก)
# ============================================================

@app.route("/")
def index():
    """หน้าแรก - ส่ง home.html กลับไปให้ browser"""
    return send_from_directory(app.static_folder, "home.html")


@app.route("/process", methods=["POST"])
def process():
    """
    🔸 ขั้นตอนหลักของระบบ:
       1. รับภาพจากหน้าเว็บ (base64)
       2. สร้าง mask & edge
       3. แบ่ง patch → ส่งเข้าโมเดล
       4. รวมผลลัพธ์กลับ → ส่งกลับไปหน้าเว็บ
    """
    try:
        start_time = time.time()     # เริ่มจับเวลา
        set_progress(0)

        # ----------- รับข้อมูลจาก Frontend -----------
        data = request.get_json()
        image_dataurl = data["image"]
        rectangles    = data["rectangles"]
        set_progress(5, "เริ่มประมวลผลภาพ...")

        # แปลง base64 → numpy array (BGR)
        img_pil = dataurl_to_pil(image_dataurl).convert("RGB")
        img_np  = np.array(img_pil)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # ----------- สร้าง mask จากกรอบที่ผู้ใช้เลือก -----------
        boxes = []
        for r in rectangles:
            x1, y1 = int(r["x"]), int(r["y"])
            x2, y2 = x1 + int(r["width"]), y1 + int(r["height"])
            boxes.append((x1, y1, x2, y2))
        mask_np = multi_box_auto_mask(img_bgr, boxes)
        set_progress(20, "สร้าง mask สำเร็จ")

        # ----------- สร้าง edge map -----------
        edge_np = create_edge_map(img_bgr)

        # บันทึกไฟล์ชั่วคราว
        cv2.imwrite(os.path.join(SAVE_DIR, "original.png"), img_bgr)
        cv2.imwrite(os.path.join(SAVE_DIR, "mask.png"), mask_np)
        cv2.imwrite(os.path.join(SAVE_DIR, "edge.png"), edge_np)

        # ----------- แบ่งภาพออกเป็น patch -----------
        n_patches, full_size = save_patches_triplet(
            img_bgr, mask_np, edge_np,
            os.path.join(SAVE_DIR, "patches_img"),
            os.path.join(SAVE_DIR, "patches_mask"),
            os.path.join(SAVE_DIR, "patches_edge"),
            prefix="patch",
            size=512,
            stride=256
        )
        set_progress(40, f"แบ่งภาพเป็น {n_patches} แพตช์")

        # ----------- คัดลอกไปโฟลเดอร์ของโมเดล -----------
        clear_and_copy(os.path.join(SAVE_DIR, "patches_img"),  os.path.join(MODEL_TEST_DIR, "input"))
        clear_and_copy(os.path.join(SAVE_DIR, "patches_mask"), os.path.join(MODEL_TEST_DIR, "mask"))
        clear_and_copy(os.path.join(SAVE_DIR, "patches_edge"), os.path.join(MODEL_TEST_DIR, "edge"))
        set_progress(60, "เตรียมข้อมูลให้โมเดล")

        # ----------- รันโมเดล restoration/inpainting -----------
        run_inference()
        set_progress(85, "โมเดลประมวลผลเสร็จ")

        # ----------- รวม patch กลับเป็นภาพเต็ม -----------
        merged_dir = os.path.join(MODEL_TEST_DIR, "merged_output")
        result_img = reassemble_patches_with_blending(merged_dir, full_size, size=512, stride=256)

        # ----------- แปลงผลลัพธ์เป็น Base64 เพื่อนำไปแสดง -----------
        _, buf = cv2.imencode(".png", result_img)
        b64 = base64.b64encode(buf).decode("utf-8")
        result_url = "data:image/png;base64," + b64

        elapsed = time.time() - start_time
        print(f"ใช้เวลา: {elapsed:.2f} วินาที")

        set_progress(100, "เสร็จสิ้น")

        # ส่งผลลัพธ์กลับเป็น JSON
        return jsonify({
            "success": True,
            "message": f"Processed {n_patches} patches in {elapsed:.2f} seconds",
            "time": elapsed,
            "result": result_url
        })

    finally:
        # ----------- ล้างไฟล์ชั่วคราวหลังทำงานเสร็จ -----------
        reset_progress()
        if os.path.exists(SAVE_DIR):
            shutil.rmtree(SAVE_DIR)
            os.makedirs(SAVE_DIR, exist_ok=True)


# ============================================================
#  🔹 ส่วนรันเซิร์ฟเวอร์ Flask
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
