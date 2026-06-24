FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y curl

RUN curl -fL -o /usr/local/bin/alloy https://github.com/grafana/alloy/releases/download/v1.9.1/alloy-linux-amd64 \
    && chmod +x /usr/local/bin/alloy

COPY config.alloy /etc/alloy/config.alloy

CMD ["alloy", "run", "--config", "/etc/alloy/config.alloy"]
