FROM python:3.10-slim

# 1. Start as root to handle system packages and folder creation
USER root

# Install essential system dependencies required for OpenCV (cv2) and OS operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# 2. CRITICAL FIX: Create the directories as root FIRST, so they exist in the file tree
RUN mkdir -p /app/models /app/server_downloads

# 3. Create the Hugging Face space user
RUN useradd -m -u 1000 user

# 4. CRITICAL FIX: Change ownership of the entire /app workspace over to the non-root user
RUN chown -R user:user /app

# 5. Copy python dependencies layout
COPY --chown=user requirements.txt /app/

# 6. Switch to the Hugging Face user safely now that permissions are locked down
USER user
ENV PATH="/home/user/.local/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 7. Copy the rest of the application files with user permissions
COPY --chown=user . /app/

# Expose standard routing port mapping interface
EXPOSE 7860

# Start production server using your correct modular entry point
CMD ["python", "main.py"]