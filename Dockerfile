# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --- FIXED SECTION ---
# Install prerequisites, add the Microsoft repo, and install the ODBC driver
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        ca-certificates \
    # Import Microsoft GPG key (without apt-key)
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor \
        | tee /usr/share/keyrings/microsoft-prod.gpg > /dev/null \
    # Add Microsoft SQL Server repo
    && curl -sSL https://packages.microsoft.com/config/debian/11/prod.list \
        | tee /etc/apt/sources.list.d/mssql-release.list \
    # Make repo use the signed key
    && sed -i 's#^deb #deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] #' /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# (Ensure pyodbc is in requirements.txt if needed)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Command to run the application
CMD gunicorn --bind 0.0.0.0:$PORT run:app
