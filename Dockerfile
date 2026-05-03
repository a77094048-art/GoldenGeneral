FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg
RUN pip3 install yt-dlp flask python-telegram-bot[webhooks]==20.0
WORKDIR /app
COPY . /app
EXPOSE 10000
CMD ["bash", "start.sh"]