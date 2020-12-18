# Create By: Ritdhwaj Singh Chandel
FROM python:3.8
RUN pip install --upgrade pip && \
    pip install -U setuptools==49.6.0
RUN apt-get update && \
    apt-get install unzip groff -y
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install
COPY requirements.txt ./

RUN pip install -r requirements.txt
