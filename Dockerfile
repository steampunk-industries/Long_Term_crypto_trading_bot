FROM tensorflow/tensorflow:2.13.0-gpu

# Set working directory
WORKDIR /app

# Install system dependencies including TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data

# Copy project files
COPY . .

# Create non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["python", "paper_trading.py", "--bot-type", "high_risk", "--duration", "86400"]
