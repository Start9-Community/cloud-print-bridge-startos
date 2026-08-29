FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ghostscript \
        libreoffice-core-nogui \
        libreoffice-writer-nogui \
        libreoffice-calc-nogui \
        libreoffice-impress-nogui \
        fonts-dejavu-core \
        fonts-liberation2 \
        fonts-crosextra-carlito \
        fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir Pillow==12.3.0 reportlab==4.4.2

# Every job is parsed by LibreOffice, Ghostscript and Pillow, so the worker runs
# unprivileged. StartOS ignores this image's USER; `main.ts` names the account.
RUN useradd --system --create-home --home-dir /home/cloudprint \
        --shell /usr/sbin/nologin cloudprint

WORKDIR /app

COPY app/worker.py /app/worker.py
COPY app/discover_printers.py /app/discover_printers.py

RUN chmod 0555 /app/worker.py /app/discover_printers.py

USER cloudprint

ENTRYPOINT ["python3", "/app/worker.py"]
