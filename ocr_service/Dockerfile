FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by OpenCV and PaddlePaddle
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements và install các dependency chung trước
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ folder PaddleOCR vừa clone vào container
COPY PaddleOCR /app/PaddleOCR

# Cài đặt PaddleOCR trực tiếp từ mã nguồn local vừa clone
RUN cd /app/PaddleOCR && pip install -e .

COPY . .

# Warm up: run a simple python statement to download model files during build time
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='vi', show_log=False)"

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
