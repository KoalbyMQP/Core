# Build from root of Core:
#
#   docker build -f pkgs/hello-ui/Dockerfile -t hello-ui:dev .
#   docker buildx build --platform linux/arm64 -f pkgs/hello-ui/Dockerfile -t hello-ui:dev-arm64 .
#
# The UI stage runs on the build machine's own platform: its output is plain JS/CSS, so an
# arm64 image needs no emulation for it.

FROM --platform=$BUILDPLATFORM node:22-slim AS ui
WORKDIR /ui
COPY pkgs/hello-ui/ui/package.json pkgs/hello-ui/ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY pkgs/hello-ui/ui/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONPATH=/opt/zara/python \
    PYTHONUNBUFFERED=1
COPY pkgs/zaraos_interfaces/zara_commands /opt/zara/python/zara_commands
COPY pkgs/hello-ui/app.py /app/app.py
# Cortex reads the app's UI from this directory: zara-ui.json + the federation build.
COPY --from=ui /ui/dist /etc/zaraos/ui
STOPSIGNAL SIGINT
CMD ["python", "/app/app.py"]
