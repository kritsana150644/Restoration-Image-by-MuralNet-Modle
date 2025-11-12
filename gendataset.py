import os
import cv2
import numpy as np
from glob import glob
from tqdm import tqdm
import random
import albumentations as A

# ========================
# CONFIGURATION
# ========================
IMG_SIZE = 512
STRIDE = 256
TRAIN_RATIO = 0.7
VAL_RATIO = 0.2
TEST_RATIO = 0.1
AUGMENT_TIMES = 2

# ========================
# AUGMENTATION PIPELINE
# ========================
augment = A.Compose([
    A.RandomRotate90(p=0.5),#หมุ่น
    A.Flip(p=0.5),#กลับด้าน
    A.RandomBrightnessContrast(p=0.5),#สุ่มแสง
    A.GaussianBlur(blur_limit=(3, 7), p=0.3),#เบลอ
    A.Sharpen(alpha=(0.1, 0.3), lightness=(0.7, 1.0), p=0.3),#ความคมชัด
    A.GaussNoise(var_limit=(10.0, 50.0), p=0.4)#เติม noise
])

# ========================
# UTILITIES
# ========================
def make_dirs(base_dir):
    for split in ['train', 'val', 'test']:
        for sub in ['images', 'masks', 'edges']:
            os.makedirs(os.path.join(base_dir, split, sub), exist_ok=True)

def split_image(img, size=512, stride=256): # ตัดภาพเป็นลูปจากบนลงล่างไปขวา
    h, w = img.shape[:2]
    patches = []
    for y in range(0, h - size + 1, stride):
        for x in range(0, w - size + 1, stride):
            patches.append(img[y:y+size, x:x+size])
    return patches

def create_edge_map(img_np):
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY) #แปลงเป็นขาวดำ
    edges = cv2.Canny(gray, 100, 200) #หาเส้นขอบ
    edge_white = np.zeros_like(edges)
    edge_white[edges > 0] = 255 #ทำเส้นขาวบนสีดำ
    return edge_white


# ========================
# ✅ ฟังก์ชันสร้าง mask
# ========================
def create_random_mask(img_np):
    h, w = img_np.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    num_strokes = random.randint(5, 12)
    for _ in range(num_strokes):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        length = random.randint(80, 250)
        thickness = random.randint(8, 18)
        direction = random.uniform(0, 2 * np.pi) #มุมเริ่มทิศทางแบบเรเดียน
        points = [(x, y)] # พิกัดของจุดตามทางเดินที่จะต่อทีหลัง
        for _ in range(length // 10):
            direction += np.random.uniform(-0.6, 0.6) #ทิศทางสุ่ม
            step = random.randint(8, 25)
            x += int(step * np.cos(direction))
            y += int(step * np.sin(direction))
            if 0 <= x < w and 0 <= y < h:
                points.append((x, y))
        for i in range(len(points) - 1):
            cv2.line(mask, points[i], points[i + 1], 255, thickness) # ต่อเส้นระหว่างจุด
    mask = cv2.GaussianBlur(mask, (7, 7), 2)
    _, mask = cv2.threshold(mask, 50, 255, cv2.THRESH_BINARY)
    return mask


# ========================
# MAIN PROCESS
# ========================
def process_images(input_folder, output_folder, augment_times=AUGMENT_TIMES):
    make_dirs(output_folder)
    image_files = glob(os.path.join(input_folder, "*.jpg")) + glob(os.path.join(input_folder, "*.png"))
    all_patches = []

    for img_path in tqdm(image_files, desc="Loading & splitting"):
        img = cv2.imread(img_path)
        if img is None or img.shape[0] < IMG_SIZE or img.shape[1] < IMG_SIZE:
            continue
        patches = split_image(img, IMG_SIZE, STRIDE)
        for patch in patches:
            mask = create_random_mask(patch)
            edge = create_edge_map(patch)
            all_patches.append((patch, mask, edge))

    print(f"\nTotal patch triplets: {len(all_patches)}")

    # ---------- แบ่ง train / val / test ----------
    random.shuffle(all_patches)
    total = len(all_patches)
    train_end = int(total * TRAIN_RATIO)
    val_end = int(total * (TRAIN_RATIO + VAL_RATIO))

    splits = {
        "train": all_patches[:train_end],
        "val": all_patches[train_end:val_end],
        "test": all_patches[val_end:]
    }

    for split, data in splits.items():
        save_img_dir  = os.path.join(output_folder, split, "images")
        save_mask_dir = os.path.join(output_folder, split, "masks")
        save_edge_dir = os.path.join(output_folder, split, "edges")

        counter = 1
        do_augment = split in ["train", "val"]

        for (img, mask, edge) in tqdm(data, desc=f"Saving {split}"):
            base_name = f"{split}_{counter:06d}.png"
            cv2.imwrite(os.path.join(save_img_dir, base_name), img)
            cv2.imwrite(os.path.join(save_mask_dir, base_name), mask)
            cv2.imwrite(os.path.join(save_edge_dir, base_name), edge)
            counter += 1

            # augment แล้วนับต่อเนื่อง
            if do_augment:
                for _ in range(augment_times):
                    aug_img = augment(image=img)["image"]
                    aug_mask = mask.copy()
                    aug_edge = create_edge_map(aug_img)
                    base_name = f"{split}_{counter:06d}.png"
                    cv2.imwrite(os.path.join(save_img_dir, base_name), aug_img)
                    cv2.imwrite(os.path.join(save_mask_dir, base_name), aug_mask)
                    cv2.imwrite(os.path.join(save_edge_dir, base_name), aug_edge)
                    counter += 1

        print(f"{split}: saved {counter-1} total files")

    print("\nDONE — Dataset generated successfully!")


# ========================
# EXECUTE
# ========================
if __name__ == "__main__":
    process_images("raw_images", "dataset/flist", augment_times=2)
