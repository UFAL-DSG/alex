FROM      ubuntu:14.04
MAINTAINER Lukas Zilka <lukas@zilka.me>

ADD alex-requirements.txt /tmp/alex-requirements.txt
ADD docker/install_dep.sh /tmp/
ADD docker/install_pykaldi.sh /tmp/install_pykaldi.sh

RUN bash /tmp/install_dep.sh && bash /tmp/install_pykaldi.sh

ADD . /app/alex

WORKDIR /app/alex
