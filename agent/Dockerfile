FROM python:3.12-slim

# grafana/mcp-grafana ships as a Go binary; install it into the image so the
# agent service can spawn it as a stdio subprocess (see second_unit/tools/grafana_mcp.py).
FROM golang:1.22-bookworm AS mcp-grafana-build
RUN go install github.com/grafana/mcp-grafana/cmd/mcp-grafana@latest

FROM python:3.12-slim
COPY --from=mcp-grafana-build /go/bin/mcp-grafana /usr/local/bin/mcp-grafana

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY second_unit/ second_unit/
COPY fixtures/ fixtures/
COPY server.py .
COPY demo_mode/ demo_mode/

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
