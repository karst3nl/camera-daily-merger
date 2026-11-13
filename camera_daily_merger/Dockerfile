# Fetch target-architecture packages without executing target binaries.
FROM alpine:3.22 AS target-base
FROM --platform=$BUILDPLATFORM alpine:3.22 AS media-tools
ARG TARGETARCH
COPY --from=target-base /etc/apk/keys/ /etc/apk/keys/
RUN --mount=type=secret,id=proxy_ca,target=/etc/ssl/cert.pem \
    case "$TARGETARCH" in arm64) apk_arch=aarch64 ;; amd64) apk_arch=x86_64 ;; *) exit 1 ;; esac; \
    apk --root /target --initdb --arch "$apk_arch" --no-scripts --no-cache \
      --keys-dir /etc/apk/keys \
      --repository https://dl-cdn.alpinelinux.org/alpine/v3.22/main \
      --repository https://dl-cdn.alpinelinux.org/alpine/v3.22/community \
      add ffmpeg=6.1.2-r2
FROM python:3.12.12-alpine3.22
COPY --from=media-tools /target/ /
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/merger
COPY app/ ./app/
COPY LICENSE THIRD_PARTY.md ./
COPY --chmod=0555 run.sh /run.sh
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["python", "-m", "app.main", "--healthcheck"]
ENTRYPOINT ["/run.sh"]
