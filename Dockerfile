# linux/amd64 release baseline; refresh digest through reviewed security rebuilds.
FROM python:3.13-slim-trixie@sha256:aaf08c5490d52cd92bc27142a5215b1e47355a5eaf9adfad2a0fbc022d0b5490 AS dependencies
ARG INSTALL_UI=false
WORKDIR /build
COPY requirements.txt requirements-ui.txt ./
RUN if [ "$INSTALL_UI" = true ]; then req=requirements-ui.txt; else req=requirements.txt; fi; \
    python -m pip install --no-cache-dir --no-deps --require-hashes --only-binary=:all: --no-compile --target=/opt/packages -r "$req"

FROM python:3.13-slim-trixie@sha256:aaf08c5490d52cd92bc27142a5215b1e47355a5eaf9adfad2a0fbc022d0b5490 AS runtime
ARG SOURCE_REVISION=uncommitted
LABEL org.opencontainers.image.title="OSS Inference Gateway" \
      org.opencontainers.image.source="https://github.com/hzjanuary/ai-gateway-chatbot" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision=$SOURCE_REVISION
RUN python -m pip uninstall -y pip && \
    groupadd --gid 10001 gateway && useradd --uid 10001 --gid gateway --create-home gateway && \
    install -d -m 0700 -o 10001 -g 10001 /var/lib/gateway
WORKDIR /app
ENV PYTHONPATH=/opt/packages:/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    GATEWAY_CONFIG_DIR=/var/lib/gateway
COPY --from=dependencies /opt/packages /opt/packages
COPY gateway /app/gateway
COPY LICENSE NOTICE /app/
COPY --chmod=755 scripts/gateway /usr/local/bin/gateway
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).close()"]
ENTRYPOINT ["gateway"]
CMD ["serve"]
