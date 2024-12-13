FROM debian:bullseye-slim

LABEL original_maintainer="Brett - github.com/brettmayson"
LABEL maintainer="CWO - github.com/c-w-o"
LABEL org.opencontainers.image.source=https://github.com/c-w-o/arma3server

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update \
    && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        python3 \
        net-tools \
        nano \
        curl \
        iputils-ping \
        lib32stdc++6 \
        lib32gcc-s1 \
        libcurl4 \
        wget \
        ca-certificates \
    && \
    apt-get remove --purge -y \
    && \
    apt-get clean autoclean \
    && \
    apt-get autoremove -y \
    && \
    rm -rf /var/lib/apt/lists/* \
    && \
    mkdir -p /steamcmd \
    && \
    wget -qO- 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz' | tar zxf - -C /steamcmd

ENV ARMA_BINARY=./arma3server
ENV ARMA_CONFIG=server.cfg
ENV BASIC_CONFIG=basic.cfg
ENV PARAM_CONFIG=parameter.cfg
ENV ARMA_PROFILE=main
ENV ARMA_WORLD=empty
ENV ARMA_LIMITFPS=60
ENV ARMA_CDLC=
ENV HEADLESS_CLIENTS=0
ENV HEADLESS_CLIENTS_PROFILE="\$profile-hc-\$i"
ENV PORT=2302
ENV STEAM_BRANCH=public
ENV STEAM_BRANCH_PASSWORD=
ENV MODS_PRESET=mods.html
ENV SKIP_INSTALL=false
ENV STEAM_USER=
ENV STEAM_PASSWORD=

EXPOSE 2302/udp
EXPOSE 2303/udp
EXPOSE 2304/udp
EXPOSE 2305/udp
EXPOSE 2306/udp

WORKDIR /tmp

VOLUME /arma3
VOLUME /steamcmd
VOLUME /var/run/share/arma3/server-common
VOLUME /var/run/share/arma3/this-server

STOPSIGNAL SIGINT

COPY launch.py /

CMD ["python3","/launch.py"]
