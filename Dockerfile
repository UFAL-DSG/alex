FROM      ufaldsg/alex
MAINTAINER Martin Vejman <vejmanm@ssakhk.cz>

# Clone Alex -en from repository.
RUN mkdir /repo
WORKDIR /repo
RUN git clone  https://github.com/m2rtin/alex.git
WORKDIR /repo/alex
RUN git checkout en

#
# en version
#

RUN mkdir /repo/alex/alex/resources/private
RUN echo "config = {}" > /repo/alex/alex/resources/private/default.cfg
RUN mkdir /repo/alex/alex/applications/call_logs

RUN /repo/alex/alex/applications/PublicTransportInfoCS/hclg/models/download_models.py
RUN /repo/alex/alex/applications/PublicTransportInfoCS/data/download_data.py
RUN /repo/alex/alex/applications/PublicTransportInfoCS/lm/download_models.py
RUN /repo/alex/alex/applications/PublicTransportInfoCS/slu/download_models.py

WORKDIR /repo/alex/alex/applications/PublicTransportInfoEN/
CMD ["sh","./vhub_private_ext_google_only_hdc_slu"]
