FROM python:3.10

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    wget \
    build-essential \
    && wget https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz \
    && tar xzf sqlite-autoconf-3420000.tar.gz \
    && cd sqlite-autoconf-3420000 \
    && ./configure --prefix=/usr/local \
    && make \
    && make install \
    && cd .. \
    && rm -rf sqlite-autoconf-3420000* \
    && ldconfig \
    && apt-get remove -y wget build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for the new SQLite
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
ENV PATH=/usr/local/bin:$PATH

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the .env file
COPY .env .env

# Copy API code
COPY api/ ./api/

# Copy required folders for API
COPY graphragtest/ ./graphragtest/
COPY rag/ ./rag/

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300", "--reload"]