FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libsdl2-image-2.0-0 \
    libgl1 \
    libgbm1 \
    libdrm2 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV SDL_VIDEODRIVER=kmsdrm
ENV SDL_AUDIODRIVER=dummy
ENV DISPLAY=

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir pygame==2.6.1

COPY src/ ./src/

CMD ["python3", "src/main.py"]