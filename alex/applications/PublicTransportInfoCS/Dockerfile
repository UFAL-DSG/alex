FROM alex
MAINTAINER Lukas Zilka <lukas@zilka.me>

# Download models.
RUN /app/alex/alex/applications/PublicTransportInfoCS/hclg/models/download_models.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/data/download_data.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/lm/download_models.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/slu/download_models.py

# Add the directory with configs.
#ADD private /app/alex/alex/resources/private

# Create directory for logs.
RUN mkdir -p /ha/projects/vystadial/data/call-logs/2013-05-30-alex-aotb-prototype/new

WORKDIR /app/alex/alex/applications/PublicTransportInfoCS

#ENTRYPOINT ./vhub_live_kaldi
