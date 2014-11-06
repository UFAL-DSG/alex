FROM      ubuntu:14.04
MAINTAINER Lukas Zilka <lukas@zilka.me>

ADD alex-requirements.txt /tmp/alex-requirements.txt
RUN docker/install_dependencies.sh
RUN docker/install_kaldi.sh
ADD . /app/alex