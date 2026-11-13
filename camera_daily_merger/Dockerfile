FROM python:3.12.12-alpine3.22
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/merger
COPY app/ ./app/
COPY --chmod=0555 run.sh /run.sh
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["python", "-m", "app.main", "--healthcheck"]
ENTRYPOINT ["/run.sh"]
