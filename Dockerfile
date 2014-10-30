FROM      ubuntu:14.04
MAINTAINER Lukas Zilka <lukas@zilka.me>

RUN apt-get update   # Run once at the beggining

# Alex prerequisites.
RUN apt-get install -y build-essential libpng12-dev libfreetype6-dev python-dev libopenblas-dev libopenblas-base liblapack-dev liblapack3 gfortran  git python python-pip libsqlite3-dev wget libsox-fmt-mp3 libsox-dev
RUN locale-gen en_US.UTF-8
RUN update-locale LANG=en_US.UTF-8

# Clone Alex from repository.
RUN mkdir /app
WORKDIR /app
RUN git clone  https://github.com/m2rtin/alex.git
RUN git checkout en
WORKDIR /app/alex
RUN sudo apt-get -y build-dep matplotlib
RUN pip install -r alex-requirements.txt
RUN pip install pystache cython flask theano
# RUN apt-get install -y python-setuptool
# RUN pip easy_install pysox
# RUN pip install --allow-unverified pyaudio --allow-unverified pyaudio pyaudio

#
# Install PyKaldi.
#
# Prerequesities.
RUN apt-get install -y build-essential libatlas-base-dev python-dev python-pip git wget
# Addid pykaldi source files
WORKDIR /app
RUN git clone https://github.com/UFAL-DSG/pykaldi.git
WORKDIR /app/pykaldi
# PyKaldi tools.
WORKDIR tools
RUN make atlas openfst_tgt
# Compile the Kaldi src.
WORKDIR ../src
RUN ./configure --shared && make && echo 'KALDI LIBRARY INSTALLED OK'
# Compile Online recogniser.
WORKDIR onl-rec
RUN make && make test && echo 'OnlineLatgenRecogniser build and test OK'
# Compile Kaldi module for Python.
WORKDIR ../../pykaldi
RUN pip install -r pykaldi-requirements.txt
RUN make install && echo 'Pykaldi build and installation files prepared: OK'
# Install locally installed Openfst to /usr/local
WORKDIR ../tools/openfst
RUN for dir in lib include bin ; do cp -r $dir /usr/local/ ; done
RUN ldconfig
# Test setup
RUN python -c 'import fst; import kaldi.decoders'
# Remove Pykaldi source files
WORKDIR /app
RUN rm -rf pykaldi



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

# others
RUN apt-get install -y libasound2-plugins libsox-fmt-all libsox-dev sox
RUN pip install --upgrade --pre pysox

RUN apt-get install -y flac

WORKDIR /app/alex/alex/resources
RUN mkdir ./private
RUN echo "config = {}" > ./private/default.cfg


RUN /app/alex/alex/applications/PublicTransportInfoCS/hclg/models/download_models.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/data/download_data.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/lm/download_models.py
RUN /app/alex/alex/applications/PublicTransportInfoCS/slu/download_models.py

WORKDIR /app/alex/alex/applications/PublicTransportInfoEN/
CMD ./vhub_private_ext_google_only_hdc_slu

