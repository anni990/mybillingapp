# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- CORRECTED SECTION ---
# Install prerequisites, add the Microsoft repo, and install the ODBC driver
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# --- OPTIMIZED SECTION ---
# Install Python dependencies from requirements.txt
# (Ensure pyodbc is listed in your requirements.txt file)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Command to run the application (chmod +x is not needed when using this format)
CMD ["python", "run.py"]