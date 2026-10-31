# Dockerfile for CivicGuard Smart City AI Tourist Crowd Monitor
# Optimized for Raspberry Pi 4 (ARM64) & x86_64, OpenCV GUI support, and CPU-efficient PyTorch
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=5000

WORKDIR /app

# Install OS libraries required by OpenCV and camera devices
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    v4l-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight PyTorch CPU first (avoids multi-gigabyte CUDA bloat on edge)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY . .

# Expose web platform port (Flask CCTV & Kiosk Server)
EXPOSE 5000

# Healthcheck for container stability
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:5000/api/stats || exit 1

# Launch the production Flask platform
CMD ["python3", "app.py"]
