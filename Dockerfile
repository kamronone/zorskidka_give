FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]




