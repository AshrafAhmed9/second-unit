FROM debian:bookworm-slim

# Headless Blender for Cloud Run Jobs. Uses the official tarball rather than
# apt so the version is pinned and reproducible for judges.
ARG BLENDER_VERSION=4.2.3
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget xz-utils libxi6 libxrender1 libxfixes3 libxxf86vm1 libgl1 \
    python3 python3-pip \
    && wget -q https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz \
    && tar -xf blender-${BLENDER_VERSION}-linux-x64.tar.xz -C /opt \
    && mv /opt/blender-${BLENDER_VERSION}-linux-x64 /opt/blender \
    && rm blender-${BLENDER_VERSION}-linux-x64.tar.xz \
    && apt-get purge -y wget xz-utils && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/blender:${PATH}"

WORKDIR /app
COPY render_worker.py .
RUN pip3 install --no-cache-dir --break-system-packages requests opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

ENTRYPOINT ["python3", "render_worker.py"]
