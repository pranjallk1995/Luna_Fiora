FROM python:3.12-slim
WORKDIR /workspace/ui
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]