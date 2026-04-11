FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget build-essential autoconf automake libtool pkg-config \
    linux-libc-dev fonts-dejavu-core \
    libdrm-dev libgbm-dev libudev-dev \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/libsdl-org/SDL/releases/download/release-2.28.4/SDL2-2.28.4.tar.gz && \
    tar xf SDL2-2.28.4.tar.gz && \
    cd SDL2-2.28.4 && \
    ./configure \
        --host=$(gcc -dumpmachine) \
        --enable-video-kmsdrm \
        --disable-video-opengl \
        --disable-video-wayland \
        --disable-video-x11 \
        --disable-pulseaudio \
        --disable-esd && \
    grep "SDL_VIDEO_DRIVER_KMSDRM 1" include/SDL_config.h || (echo "KMSDRM NOT IN CONFIG" && exit 1) && \
    make -j$(nproc) && make install && \
    cd .. && rm -rf SDL2-2.28.4*

COPY pyproject.toml .
RUN pip install --no-cache-dir --target /app/deps pygame==2.6.1 && \
    ln -sf /usr/local/lib/libSDL2-2.0.so.0 \
    $(find /app/deps -name "libSDL2-2-*.so*" | head -1)


FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libdrm2 libgbm1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/libSDL2-2.0.so.0* /usr/local/lib/
COPY --from=builder /app/deps /app/deps
COPY --from=builder /usr/share/fonts /usr/share/fonts

RUN ldconfig

ENV SDL_VIDEODRIVER=kmsdrm
ENV SDL_AUDIODRIVER=dummy
ENV PYTHONPATH=/app/deps

COPY src/ /app/src/
CMD ["python3", "/app/src/main.py"]
