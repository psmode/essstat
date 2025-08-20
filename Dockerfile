FROM python:3

WORKDIR /essstat

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "essstat.py"]
