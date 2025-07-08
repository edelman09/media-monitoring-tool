# Use official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies for Chromium + Selenium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    build-essential \
    libnss3 \
    libxss1 \
    libasound2 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libgbm1 \
    libgtk-3-0 \
    libxshmfence1 \
    libxrandr2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3-dev \
    libgconf-2-4 \
    libfontconfig1 \
    libxi6 \
    libxtst6 \
    libxss1 \
    libgconf-2-4 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgtk-3-0 \
    libgtk-4-1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    PATH=$PATH:/usr/bin

# Ensure chromedriver has proper permissions
RUN chmod +x /usr/bin/chromedriver

# Copy dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Download NLTK data
RUN python -m nltk.downloader punkt stopwords wordnet

# Copy application code
COPY . .

# Create downloads directory
RUN mkdir -p /app/downloads

# Expose Streamlit port
EXPOSE 8501

# Avoid Streamlit telemetry prompts
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true

# Run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
