FROM ufaldsg/alex-base
MAINTAINER Lukas Zilka <lukas@zilka.me>

# Download models.
RUN /app/alex/alex/applications/PublicTransportInfoEN/hclg/models/download_models.py
RUN /app/alex/alex/applications/PublicTransportInfoEN/data/download_data.py
RUN /app/alex/alex/applications/PublicTransportInfoEN/lm/download_models.py

WORKDIR /app/alex/alex/applications/PublicTransportInfoEN
