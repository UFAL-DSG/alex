#!/bin/bash
set -e

docker build -t ufaldsg/alex-base .
docker build -t ufaldsg/alex-ptics alex/applications/PublicTransportInfoCS
docker build -t ufaldsg/alex-ptien alex/applications/PublicTransportInfoEN
