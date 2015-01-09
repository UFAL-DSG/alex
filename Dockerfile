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



# ===============TEMPORARY BEFORE MASTER PULL==============
#
# Install PjSip & its Python module.
#
WORKDIR /app/
RUN git clone https://github.com/UFAL-DSG/pjsip.git
WORKDIR /app/pjsip
RUN ./configure CXXFLAGS=-fPIC CFLAGS=-fPIC LDFLAGS=-fPIC CPPFLAGS=-fPIC
RUN make dep
RUN make
RUN make install
WORKDIR /app/pjsip/pjsip-apps/src/python/
RUN python setup-pjsuaxt.py install

# PyAudio
WORKDIR /app/
RUN apt-get install -y portaudio19-dev
RUN git clone https://github.com/bastibe/PyAudio.git
WORKDIR /app/PyAudio
RUN python setup.py install
#
# =========================================================

RUN apt-get install flac

WORKDIR /repo/alex/alex/applications/PublicTransportInfoEN/
CMD ["sh","./vhub_private_ext_google_only_hdc_slu"]
