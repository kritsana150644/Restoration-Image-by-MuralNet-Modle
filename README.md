#Restoration of Thai Mural Paintings using MuralNet Model  
### การบูรณะภาพจิตรกรรมฝาผนังไทยด้วยโมเดล MuralNet

---

## Project Overview | ภาพรวมของโครงการ

This project aims to **restore and enhance damaged Thai mural paintings** using deep learning–based inpainting techniques.  
We fine-tuned and extended the **MuralNet** model for **Thai mural restoration**, developed a **Flask web interface**, and created a **custom dataset** for real-world applications.

โครงการนี้มุ่งเน้นการ **บูรณะภาพจิตรกรรมฝาผนังไทยที่ชำรุดเสียหาย**  
โดยใช้เทคนิค **Deep Learning ในการเติมเต็มส่วนที่ขาดหายของภาพ (Image Inpainting)**  
ผ่านโมเดล **MuralNet** ที่ได้รับการปรับแต่ง (Fine-tune) ให้เหมาะสมกับภาพจิตรกรรมไทย  
พร้อมทั้งพัฒนา **Web Application** เพื่อใช้งานจริง

---

## Model & Methodology | โมเดลและกระบวนการ

1. **Edge Detection** – สร้างแผนที่เส้นขอบ (Edge map) เพื่อเป็นแนวทางให้โมเดลบูรณะภาพ  
2. **Mask Generation** – สร้างมาสก์อัตโนมัติระบุบริเวณที่ชำรุด  
3. **MuralNet Inpainting** – ใช้ CNN ในการเติมเต็มส่วนที่หายไป

---

## System Overview | สถาปัตยกรรมระบบ

Input → Auto Mask → Edge Detection → MuralNet Inpainting → Output

yaml
คัดลอกโค้ด

| ส่วนประกอบ | รายละเอียด |
|-------------|-------------|
| **Frontend (Flask Web UI)** | ระบบอัปโหลด/แสดงผลภาพแบบเรียลไทม์ |
| **Backend (Python)** | ประมวลผลภาพ, รันโมเดล, รวมภาพหลังบูรณะ |
| **Model (MuralNet)** | โมเดล CNN สำหรับการเติมเต็มภาพ |

---

## Installation | การติดตั้ง

```bash
git clone https://github.com/kritsana150644/Restoration-Image-by-MuralNet-Modle.git
cd Restoration-Image-by-MuralNet-Modle
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
แล้วเปิดเว็บที่ http://127.0.0.1:5000/

Evaluation Metrics
Metric	Description
PSNR	วัดความเหมือนของภาพที่บูรณะกับต้นฉบับ
LPIPS	วัดคุณภาพเชิงการรับรู้ (Perceptual similarity)

Due to file size limits, please download the dataset here:
Google Drive Link 

Developer
Kritsana Charoenkij
Faculty of Information Technology, Silpakorn University
Advisor: Asst. Prof. Dr. Sunisa Pongpinijpinyo

Email: kritsana2544.oc@gmail.com
GitHub: @kritsana150644

Credits
This project is based on the original MuralNet implementation by
qinnzou/mural-image-inpainting

We have fine-tuned and expanded it for Thai mural restoration,
with additional dataset preparation, automatic mask generation,
and a web-based interface for real-world use.

