let selectedFile = null;
let canvas = null;
let ctx = null;
let img = null;
let scale = 1;
let offsetX = 0;
let offsetY = 0;
let imgWidth = 0;
let imgHeight = 0;
let rectangles = [];
let isDrawing = false;
let startX, startY;
let currentRect = null;
let restoredImageData = null;
let isPanning = false;
let lastPanX, lastPanY;
let initialScale = 1;
let initialOffsetX = 0;
let initialOffsetY = 0;

// ✅ เก็บค่า progress ปัจจุบัน
let currentProgress = 0;

// Initialize when page loads
document.addEventListener("DOMContentLoaded", function () {
  initializeUpload(); // เตรียมระบบอัปโหลดไฟล์
  initializeCanvas(); // เตรียม canvas สำหรับวาด/ซูม
});

function initializeUpload() {
  // ดึง element upload-area และ input file
  const uploadArea = document.getElementById("upload-area");
  const fileInput = document.getElementById("file-input");
  // เมื่อคลิกที่ upload-area → เปิดช่องเลือกไฟล์
  uploadArea.addEventListener("click", () => fileInput.click());
  // รองรับการลากวางไฟล์
  uploadArea.addEventListener("dragover", handleDragOver);
  uploadArea.addEventListener("drop", handleDrop);
  uploadArea.addEventListener("dragleave", handleDragLeave);
  // เลือกไฟล์จาก file dialog
  fileInput.addEventListener("change", handleFileSelect);
}

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById("upload-area").classList.add("dragover");  // เพิ่มเอฟเฟกต์ตอนลากเข้า
}

function handleDragLeave(e) {
  e.preventDefault();// ป้องกันการรีเฟรช
  document.getElementById("upload-area").classList.remove("dragover");// เอาเอฟเฟกต์ออก
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById("upload-area").classList.remove("dragover");
  const files = e.dataTransfer.files;// ดึงไฟล์ที่ถูกลากมา
  if (files.length > 0) {
    processFile(files[0]);// ส่งไฟล์แรกไปประมวลผล
  }
}

function handleFileSelect(e) {
  const file = e.target.files[0];// ดึงไฟล์ที่เลือก
  if (file) {
    processFile(file);// ส่งไฟล์ไปโหลดบน canvas
  }
}

function processFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("กรุณาเลือกไฟล์ภาพเท่านั้น");
    return;
  }
  if (file.size > 50 * 1024 * 1024) {
    alert("ขนาดไฟล์ใหญ่เกินไป (สูงสุด 50MB)");
    return;
  }
  selectedFile = file;
  loadImageToCanvas(file);// โหลดขึ้น canvas
}

function loadImageToCanvas(file) {
  const reader = new FileReader();
  reader.onload = function (e) {
    img = new Image(); // สร้าง ภาพใหม่
    img.onload = function () { 
      setupCanvas();// ตั้งค่าขนาด canvas ตามภาพ
      // ซ่อนหน้าจอ upload แล้วแสดง editor
      document.getElementById("upload-section").style.display = "none";
      document.getElementById("editor-section").style.display = "block";
      document.getElementById("process-btn").style.display = "inline-block";
    };
    img.src = e.target.result;// แปลงไฟล์เป็น base64 แล้วโหลดเข้า image
  };
  reader.readAsDataURL(file);// อ่านไฟล์ภาพเป็น Data URL
}

function initializeCanvas() {
  canvas = document.getElementById("editor-canvas");
  ctx = canvas.getContext("2d");

  // Mouse events
  canvas.addEventListener("mousedown", handleMouseDown);
  canvas.addEventListener("mousemove", handleMouseMove);
  canvas.addEventListener("mouseup", handleMouseUp);
  canvas.addEventListener("wheel", handleWheel);

  // Prevent default drag behavior
  canvas.addEventListener("dragstart", (e) => e.preventDefault());

  // Control buttons
  document.getElementById("zoom-in-btn").addEventListener("click", zoomIn);
  document.getElementById("zoom-out-btn").addEventListener("click", zoomOut);
  document.getElementById("reset-zoom-btn").addEventListener("click", resetZoom);
  document.getElementById("undo-btn").addEventListener("click", undoLastRectangle);
  document.getElementById("clear-btn").addEventListener("click", clearAllRectangles);
}

function setupCanvas() {
  const maxWidth = 800;
  const maxHeight = 500;
  // เก็บขนาดภาพจริง
  imgWidth = img.width;
  imgHeight = img.height;
  let displayWidth = imgWidth;
  let displayHeight = imgHeight;
  // ปรับให้ภาพไม่เกินขนาดที่กำหนด
  if (displayWidth > maxWidth) {
    displayHeight = (displayHeight * maxWidth) / displayWidth;
    displayWidth = maxWidth;
  }
  if (displayHeight > maxHeight) {
    displayWidth = (displayWidth * maxHeight) / displayHeight;
    displayHeight = maxHeight;
  }

  // ✅ ให้ขนาด attribute และ style ตรงกัน
  canvas.width = displayWidth;
  canvas.height = displayHeight;
  canvas.style.width = displayWidth + "px";
  canvas.style.height = displayHeight + "px";

  scale = displayWidth / imgWidth;
  offsetX = 0;
  offsetY = 0;
  initialScale = scale;
  initialOffsetX = offsetX;
  initialOffsetY = offsetY;

  drawCanvas();
}

function resetZoom() {
  scale = initialScale;
  offsetX = initialOffsetX;
  offsetY = initialOffsetY;
  drawCanvas();
}

function zoomAtPoint(centerX, centerY, factor) {
  const imgX = (centerX - offsetX) / scale;
  const imgY = (centerY - offsetY) / scale;
  const newScale = Math.max(0.1, Math.min(10, scale * factor));

  if (newScale !== scale) {
    scale = newScale;
    offsetX = centerX - imgX * scale;
    offsetY = centerY - imgY * scale;
    drawCanvas();
  }
}

function zoomIn() {
  zoomAtPoint(canvas.width / 2, canvas.height / 2, 1.2);
}

function zoomOut() {
  zoomAtPoint(canvas.width / 2, canvas.height / 2, 0.8);
}

function drawCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#f8f9fa";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const drawWidth = imgWidth * scale;
  const drawHeight = imgHeight * scale;
  ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);
  // ตั้งค่ารูปแบบกรอบ
  ctx.strokeStyle = "#FF6B35";
  ctx.lineWidth = 3;
  ctx.setLineDash([5, 5]);

  rectangles.forEach((rect) => {
    const x = rect.x * scale + offsetX;
    const y = rect.y * scale + offsetY;
    const width = rect.width * scale;
    const height = rect.height * scale;
    ctx.strokeRect(x, y, width, height);
  });

  if (currentRect) {
    const x = currentRect.x * scale + offsetX;
    const y = currentRect.y * scale + offsetY;
    const width = currentRect.width * scale;
    const height = currentRect.height * scale;
    ctx.strokeRect(x, y, width, height);
  }
}
// แปลงตำแหน่งของเมาส์ให้ตรงกับพิกเซลบน canvas
function getMousePos(canvas, evt) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return {
    x: (evt.clientX - rect.left) * scaleX,
    y: (evt.clientY - rect.top) * scaleY,
  };
}

function handleMouseDown(e) {
  const { x: mouseX, y: mouseY } = getMousePos(canvas, e);
  // ถ้ากด Ctrl → เข้าโหมดแพน (ลากภาพ)
  if (e.ctrlKey || e.metaKey) {
    isPanning = true;
    lastPanX = mouseX;
    lastPanY = mouseY;
    canvas.style.cursor = "grabbing";
    return;
  }
  // เช็คอยู่ในพื้นที่ของภาำไหม
  const drawWidth = imgWidth * scale;
  const drawHeight = imgHeight * scale;
  if (mouseX < offsetX || mouseX > offsetX + drawWidth || mouseY < offsetY || mouseY > offsetY + drawHeight) {
    return;
  }
  // เริ่มวาดกรอบใหม่
  isDrawing = true;
  canvas.style.cursor = "crosshair";
  startX = (mouseX - offsetX) / scale;
  startY = (mouseY - offsetY) / scale;
  currentRect = null;
}

function handleMouseMove(e) {
  const { x: mouseX, y: mouseY } = getMousePos(canvas, e);
  // เปลี่ยน cursor ตามสถานะ
  const drawWidth = imgWidth * scale;
  const drawHeight = imgHeight * scale;
  const insideImage =
    mouseX >= offsetX &&
    mouseX <= offsetX + drawWidth &&
    mouseY >= offsetY &&
    mouseY <= offsetY + drawHeight;

  if (e.ctrlKey || e.metaKey) {
    canvas.style.cursor = isPanning ? "grabbing" : "grab";
  } else if (isDrawing) {
    canvas.style.cursor = "crosshair";
  } else if (insideImage) {
    canvas.style.cursor = "crosshair";
  } else {
    canvas.style.cursor = "default";
  }

  if (isPanning) {
    const deltaX = mouseX - lastPanX;
    const deltaY = mouseY - lastPanY;
    offsetX += deltaX;
    offsetY += deltaY;
    lastPanX = mouseX;
    lastPanY = mouseY;
    drawCanvas();
    return;
  }

  if (!isDrawing) return;
  // อัปเดตกรอบที่กำลังวาด
  const imgMouseX = (mouseX - offsetX) / scale;
  const imgMouseY = (mouseY - offsetY) / scale;
  const clampedX = Math.max(0, Math.min(imgWidth, imgMouseX));
  const clampedY = Math.max(0, Math.min(imgHeight, imgMouseY));

  currentRect = {
    x: Math.min(startX, clampedX),
    y: Math.min(startY, clampedY),
    width: Math.abs(clampedX - startX),
    height: Math.abs(clampedY - startY),
  };

  drawCanvas();
}

function handleMouseUp(e) {
  const { x: mouseX, y: mouseY } = getMousePos(canvas, e);

  if (isPanning) {
    isPanning = false;
    canvas.style.cursor = e.ctrlKey || e.metaKey ? "grab" : "default";
    return;
  }

  if (!isDrawing) return;
  isDrawing = false;
  canvas.style.cursor = "default";

  if (currentRect && currentRect.width > 5 && currentRect.height > 5) {
    rectangles.push({ ...currentRect });
    updateControlButtons();
  }

  currentRect = null;
  drawCanvas();
}
//หมุนล้อเมาส์เพื่อซูมเข้า-ออก
function handleWheel(e) {
  e.preventDefault();
  const { x: mouseX, y: mouseY } = getMousePos(canvas, e);
  const imgMouseX = (mouseX - offsetX) / scale;
  const imgMouseY = (mouseY - offsetY) / scale;
  const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
  const newScale = Math.max(0.1, Math.min(10, scale * zoomFactor));

  if (newScale !== scale) {
    scale = newScale;
    offsetX = mouseX - imgMouseX * scale;
    offsetY = mouseY - imgMouseY * scale;
    drawCanvas();
  }
}

function undoLastRectangle() { // ลบกรอบสุดท้ายที่วาด
  if (rectangles.length > 0) {
    rectangles.pop();
    updateControlButtons();
    drawCanvas();
  }
}

function clearAllRectangles() {// ลบทุกกรอบ
  rectangles = [];
  updateControlButtons();
  drawCanvas();
}

function updateControlButtons() {
  const undoBtn = document.getElementById("undo-btn");
  const clearBtn = document.getElementById("clear-btn");
  const hasRectangles = rectangles.length > 0;
  undoBtn.disabled = !hasRectangles;// ปิดปุ่มถ้าไม่มีกรอบ
  clearBtn.disabled = !hasRectangles;
}
// ================================
// ✅ START PROCESSING
// ================================
async function startProcessing() {
  if (rectangles.length === 0) {
    alert("กรุณาเลือกพื้นที่ที่ต้องการฟื้นฟูก่อน");
    return;
  }

  // เตรียมภาพ original (เต็มขนาดจริง)
  const tempCanvas = document.createElement("canvas");
  tempCanvas.width = img.width;
  tempCanvas.height = img.height;
  const tempCtx = tempCanvas.getContext("2d");
  tempCtx.drawImage(img, 0, 0);
  const originalImageDataUrl = tempCanvas.toDataURL("image/png");

  const payload = {
    image: originalImageDataUrl,
    rectangles: rectangles,
  };

  // ส่วน progress bar
  const progressSection = document.getElementById("progress-section");
  const progressFill = document.getElementById("progress-fill");
  const progressText = document.getElementById("progress-text");
  const timeInfo = document.getElementById("time-info");

  progressSection.style.display = "block";
  document.getElementById("process-btn").style.display = "none";
  timeInfo.textContent = "";

  currentProgress = 0; // reset ทุกครั้งที่เริ่มใหม่
  progressFill.style.width = "0%";
  progressText.textContent = "กำลังประมวลผล... 0%";

  // ✅ polling progress
  let polling = true;

  async function pollProgress() {
    if (!polling) return;
    try {
      const res = await fetch("/status");
      const data = await res.json();
      let target = data.progress;
      let message = data.message || "";

      // ✅ ให้ progress วิ่งทีละ % จนถึง target
      let step = setInterval(() => {
        if (currentProgress >= target) {
          clearInterval(step);
        } else {
          currentProgress++;
          progressFill.style.width = currentProgress + "%";
          progressText.textContent = `กำลังประมวลผล... ${currentProgress}% (${message})`;
        }
      }, 30);

      if (data.progress < 100) {
        setTimeout(pollProgress, 1000);
      }
    } catch (err) {
      console.error("Error polling progress:", err);
    }
  }

  pollProgress();

  // ✅ ส่งข้อมูลไป backend
  try {
    const res = await fetch("/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    polling = false;

    if (data.success) {
      showResultOnCanvas(data.result);
      if (data.time) {
        timeInfo.textContent = `ใช้เวลา: ${data.time.toFixed(2)} วินาที`;
      }
    } else {
      alert("❌ เกิดข้อผิดพลาด: " + data.message);
    }
  } catch (err) {
    console.error("❌ Error:", err);
    alert("เกิดข้อผิดพลาดที่ backend");
  }
}

// ================================
// ✅ SHOW RESULT ON CANVAS
// ================================
function showResultOnCanvas(resultUrl) {
  const progressSection = document.getElementById("progress-section");
  const resultSection = document.getElementById("result-section");
  const restoredResult = document.getElementById("restored-result");

  // ซ่อน progress bar
  progressSection.style.display = "none";

  // ✅ โหลดภาพที่ผ่านการฟื้นฟูมาแทนใน canvas
  img = new Image();
  img.onload = function () {
    rectangles = [];
    setupCanvas();
    updateControlButtons();
    document.getElementById("process-btn").style.display = "inline-block";
  };
  img.src = resultUrl;

  // ✅ แสดงผลลัพธ์
  restoredResult.src = resultUrl;
  resultSection.style.display = "block";

  // เก็บผลลัพธ์ไว้สำหรับดาวน์โหลด
  restoredImageData = resultUrl;
}

// ================================
// ✅ DOWNLOAD RESULT
// ================================
function downloadResult() {
  const restoredResult = document.getElementById("restored-result");
  if (!restoredResult.src) return;

  const link = document.createElement("a");
  link.href = restoredResult.src;
  link.download = "restored_mural.png";
  link.click();
}

// ================================
// ✅ CHANGE IMAGE (อัพโหลดใหม่)
// ================================
function changeImage() {
  // Reset all states
  selectedFile = null;
  rectangles = [];
  scale = 1;
  offsetX = 0;
  offsetY = 0;
  img = null;
  restoredImageData = null;

  // Clear canvas
  if (canvas && ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  // Reset file input
  document.getElementById("file-input").value = "";

  // Reset upload area display
  const uploadArea = document.getElementById("upload-area");
  uploadArea.innerHTML = `
    <div class="upload-icon">📷</div>
    <div class="upload-text">ลากไฟล์ภาพมาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์</div>
    <div class="upload-subtext">รองรับไฟล์: JPG, PNG, JPEG (ขนาดไม่เกิน 10MB)</div>
  `;

  // Hide all sections except upload
  document.getElementById("upload-section").style.display = "block";
  document.getElementById("editor-section").style.display = "none";
  document.getElementById("progress-section").style.display = "none";
  document.getElementById("result-section").style.display = "none";

  // Reset control buttons
  updateControlButtons();

  // Show success message
  const changeBtn = document.getElementById("change-image-btn");
  const originalText = changeBtn.innerHTML;
  changeBtn.innerHTML = "✅ พร้อมอัพโหลดรูปใหม่";
  changeBtn.style.background = "linear-gradient(145deg, #28a745, #34ce57)";

  // เปลี่ยนกลับหลัง 2 วินาที
  setTimeout(() => {
    changeBtn.innerHTML = originalText;
    changeBtn.style.background = "";
  }, 2000);
}
