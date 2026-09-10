FROM python3.8-slim

WORKDIR /app

COPY . . 

RUN pip install flask redis 

EXPOSE 5000 

CMD ["python3", "app.py"]