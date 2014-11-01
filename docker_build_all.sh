#!/bin/bash

docker build -t alex .
docker build -t alex-ptics alex/applications/PublicTransportInfoCS
