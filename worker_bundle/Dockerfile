FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# System deps: Tesseract OCR + OpenCV libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# PyTorch CUDA 12.4 — whl bundles its own CUDA runtime, no system CUDA needed.
# nvidia-container-toolkit (runtime: nvidia in compose) exposes the GPU device.
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cu124

# EasyOCR + all other pipeline deps
COPY requirements.txt .
RUN pip install --no-cache-dir easyocr -r requirements.txt

# Copy processing library + worker
COPY src/ ./src/
COPY data/ ./data/
COPY worker/worker.py ./worker.py

CMD ["python", "-u", "worker.py"]
