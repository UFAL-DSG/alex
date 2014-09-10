FROM      ubuntu
MAINTAINER Lukas Zilka <lukas@zilka.me>

# Alex prerequisites.
RUN apt-get update && apt-get install -y build-essential libpng12-dev libfreetype6-dev python-dev libopenblas-dev libopenblas-base liblapack-dev liblapack3 gfortran  git python python-pip libsqlite3-dev wget
RUN locale-gen en_US.UTF-8

# Clone Alex from repository.
RUN mkdir /app
WORKDIR /app
RUN git clone https://github.com/UFAL-DSG/alex.git
WORKDIR /app/alex
RUN pip install -r alex-requirements.txt
RUN pip install pystache cython flask theano
RUN pip install --allow-unverified pyaudio --allow-unverified pyaudio pyaudio

#
# Install PyKaldi.
#

# Prerequesities.
RUN apt-get install -y build-essential libatlas-base-dev python-dev python-yaml git libportaudio-dev portaudio19-dev libsox-dev
RUN easy_install pysox

WORKDIR /app
RUN git clone https://github.com/ticcky/pykaldi/
WORKDIR /app/pykaldi

# PyKaldi tools.
WORKDIR tools
RUN make atlas openfst_tgt
RUN ldconfig
RUN pip install pyfst

# Compile the Kaldi src.
WORKDIR ../src
RUN ./configure --shared && make depend && make && echo 'KALDI LIBRARY INSTALLED OK'

# Compile Online recogniser.
WORKDIR onl-rec
RUN make depend && make && make test && echo 'OnlineLatgenRecogniser build OK'

# Compile Kaldi module for Python.
WORKDIR ../pykaldi
RUN make && echo 'INSTALLATION Works OK'
RUN make install
RUN ldconfig

# Misc.
WORKDIR /app/pykaldi/egs/vystadial/online_demo/
RUN make gmm-latgen-faster

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