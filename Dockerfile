ARG CACHE_BUST=1

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Limpeza + atualização
RUN apt-get clean
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    git bash tar wget nano vim htop \
    curl ca-certificates software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    openjdk-17-jdk && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    rm -rf /var/lib/apt/lists/*

# Verificar instalações
RUN java -version && python --version

# Clone workspace
RUN mkdir /workspace && \
    git clone https://github.com/gabrielranulfo/polars-benchmark.git /workspace

WORKDIR /workspace/

RUN git checkout mestrado

# Ambiente virtual + dependências
RUN python3.11 -m venv .venv && \
    ./.venv/bin/pip install --upgrade pip polars && \
    ./.venv/bin/pip install -r requirements.in && \
    ./.venv/bin/pip install -r requirements-polars-only.txt && \
    chmod +x *.sh

# Executa script inicial
RUN ./run.sh

CMD ["tail", "-f", "/dev/null"]
