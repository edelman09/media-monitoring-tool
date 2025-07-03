# Use an official lightweight Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxrandr2 \
    xdg-utils \
    wget \
    curl \
    unzip \
    chromium-driver \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chrome
ENV CHROME_BIN=/usr/bin/chromium \
    PATH=$PATH:/usr/bin

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Download necessary NLTK corpora
RUN python -m nltk.downloader punkt stopwords wordnet

# Copy app code into the container
COPY . .

# Expose Streamlit's default port
EXPOSE 8080

# Streamlit configuration to avoid asking for user input
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
