#!/bin/bash
set -e

apt-get install -y \
        build-essential \
        cmake \
        git \
        gcc-4.7 \
        g++-4.7 \
        libatlas-base-dev \
        python-dev \
        python-pip \
        python-software-properties \
        software-properties-common \
        subversion \
        texlive \
        texlive-latex-extra \
        wget \
        zip \
        zlib1g-dev
# Get rid of texlive and texlive-latex-extra it is needed just by irstlm to build pdf manual ;-)!

pushd /app
svn -r 769 co --non-interactive --trust-server-cert https://svn.code.sf.net/p/irstlm/code/trunk irstlm

pushd irstlm
	cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$(INSTALL_PREFIX)"
  make
  make install
popd # irstlm

