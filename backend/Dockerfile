FROM python:3.11

WORKDIR /app

# Step 1: copy only requirements first (better caching)
COPY requirements.txt ./

# Step 2: install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 3: copy full backend code
COPY . .

# Step 4: expose port
EXPOSE 8000

# Step 5: run FastAPI using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]