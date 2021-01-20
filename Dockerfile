FROM python:3.8
RUN pip install --upgrade pip && \
    pip install -U setuptools==49.6.0
RUN apt-get update && \
    apt-get install unzip groff -y
COPY requirements.txt ./

RUN pip install -r requirements.txt
