FROM ufaldsg/alex-base
MAINTAINER Lukas Zilka <lukas@zilka.me>

# Download models.
RUN /app/alex/alex/applications/PublicTransportInfoCS/hclg/models/download_models.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/data/download_data.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/lm/download_models.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/slu/dailogregclassifier/download_models.py

WORKDIR /app/alex/alex/applications/PublicTransportInfoCS
