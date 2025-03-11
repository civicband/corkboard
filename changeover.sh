#!/bin/bash

cd ../civic-band/ && \
    /usr/bin/docker compose down sites_datasette_blue && \
    cd ../corkboard/ && \
    /usr/bin/docker compose up sites_datasette_blue -d --remove-orphans && \
    cd ../civic-band/ && \
    /usr/bin/docker compose down sites_datasette_green && \
    cd ../corkboard/ && \
    /usr/bin/docker compose up sites_datasette_green -d --remove-orphans