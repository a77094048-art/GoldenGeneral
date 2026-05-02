FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install flask python-telegram-bot[webhooks]==20.0 requests beautifulsoup4 qrcode Pillow
WORKDIR /app
COPY . /app
EXPOSE 10000
CMD ["bash", "start.sh"]