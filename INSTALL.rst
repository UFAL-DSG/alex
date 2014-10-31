Installation of Alex and the dependencies
=========================================

This document describes how to install all dependencies needed to use Alex.
The Alex project is developed in Python and tested with version 2.7.
It may be necessary to have exactly this version of Python for the project
to work correctly.

Ubuntu 12.04
------------
Ask the root on the computer to run:

.. code-block:: bash

  sudo apt-get install gfortran libatlas-base-dev portaudio19-dev swig \
      flac speex sox libsox-dev mplayer libsqlite3-dev python-wxgtk2.8 libmad0-dev \
      libjpeg8-dev libfreetype6-dev libpng12-dev libagg-dev libatlas3-base \
      libsox-fmt-mp3

To get latest versions of the following python packages, I recommend to run these commands:

.. code-block:: bash

  sudo pip install --upgrade -r alex-requirements.txt
  # The following step is optional as it installs dependencies specific for performing
  # only certain tasks (like evaluating VAD performance).
  sudo pip install --upgrade -r alex-requirements-dev.txt
  sudo easy_install pysox
  

See ``alex-dsg/alex-requirements.txt``.

Source code compiled packages
-----------------------------

pyAudio
~~~~~~~
Get a special version of ``pyAudio`` from https://github.com/bastibe/PyAudio (bastibe-PyAudio-2a08fa7).
This version supports non-blocking audio.

.. code-block:: bash

  git clone https://github.com/bastibe/PyAudio.git
  cd PyAudio
  sudo python ./setup.py install

flite
~~~~~
Get the latest ``flite`` from http://www.festvox.org/flite/download.html and build it by following the these commands:

.. code-block:: bash

  wget http://www.festvox.org/flite/packed/flite-1.4/flite-1.4-release.tar.bz2
  tar -xvjf flite-1.4-release.tar.bz2
  cd flite-1.4-release
  ./configure
  make

Copy the ``flite-1.4-release/bin/flite`` file into you search path. E.g. link the ``flite`` program to your
bin directory.

HTK
~~~~
Get the latest HTK (3.4.1 tested) from http://htk.eng.cam.ac.uk/download.shtml . Build and install the HTK following
the HTK's instructions.

KALDI
~~~~~
In order to use Kaldi decoder, build ``pykaldi`` fork of Kaldi from https://github.com/UFAL-DSG/pykaldi,
install patched ``OpenFST`` from ``pykaldi``, then ``pyfst`` from https://github.com/UFAL-DSG/pyfst, and finally 
install ``pykaldi`` Python extension.

First,  build Kaldi fork ``pykaldi`` as follows:

.. code-block:: bash

  git clone https://github.com/UFAL-DSG/pykaldi
  cd pykaldi/tools
  make atlas   # Just downloads headers
  make openfst_tgt  # Install patched OpenFST LOCALLY!
  cd ../src
  ./configure  # Should find ATLAS libraries which you have installed via apptitude (easier way).
  make && make test
  cd onl-rec && make && make test  # Directory needed for pykaldi Python wrapper

Install patched ``OpenFST`` system wide. The following commands install the already built ``OpenFST`` 
library from previous step:

.. code-block:: bash

    cd pykaldi/tools/openfst
    ./configure  --prefix=/usr  # Sets the path to system wide installation directory
    sudo make install  # Copies the already built and pathced libraries from 'make openfst_tgt' step.


Install ``pyfst`` by

.. code-block:: bash

    sudo pip install --upgrade pystache pyyaml cython
    
    git clone https://github.com/UFAL-DSG/pyfst.git pyfst
    cd pyfst
    sudo python setup.py install


Finally, install the ``pykaldi`` Python extension (a wrapper around Kaldi decoders):

.. code-block:: bash

    cd pykaldi/src/pykaldi
    sudo make install


SRILM
~~~~~
Get the latest SRILM (1.6 tested) from http://www.speech.sri.com/projects/srilm/ . Build and install the SRILM following
their instructions.

pjsip
~~~~~
Get the supported pjsip 2.1 from our fork at GitHub.
To install ``pjsip``, follow these instructions:

.. code-block:: bash

  git clone git@github.com:UFAL-DSG/pjsip.git
  cd pjsip
  ./configure CXXFLAGS=-fPIC CFLAGS=-fPIC LDFLAGS=-fPIC CPPFLAGS=-fPIC
  make dep
  make
  sudo make install

then 

.. code-block:: bash

  cd pjsip-apps/src/python/
  sudo python setup-pjsuaxt.py install

This will install the ``pjsuaxt`` library.

Morfodita
~~~~~~~~~

Get the supported morfodita from GitHub.
To install ``morfodita``, follow these instructions:

.. code-block:: bash

  git clone git@github.com:ufal/morphodita.git
  cd morphodita/src
  make
  cd ../bindings/python
  make PYTHON_INCLUDE=/usr/include/python2.7/

  sudo cp -R ./ufal /usr/local/lib/python2.7/dist-packages
  sudo cp ./ufal_morphodita.so /usr/local/lib/python2.7/dist-packages


OpenJulius
~~~~~~~~~~
Get the supported Open Julius ASR decoder (4.2.3 tested) from our fork at GitHub.
To install ``openjulius``, follow the following instructions:

.. code-block:: bash

  git clone git@github.com:UFAL-DSG/openjulius.git
  cd openjulius
  ./configure
  make
  make install

Optimised ATLAS and LAPACK libraries
------------------------------------
If you need optimised ATLAS and LAPACK libraries then you have to compile them on your own.
Then modify config for numpy. Optimised ATLAS and LAPACK can compute matrix multiplication on all CPU cores available.

To build your own optimised ATLAS and LAPACK libraries:

- get latest LAPACK
- get latest ATLAS
- compile lapack
- tell atlas where is your compiled LAPACK
- compile ATLAS

Local installation of Python 2.7 and its dependencies
-----------------------------------------------------
If you do not have the root access to the machine then you then you can use https://github.com/akheron/multipy to install
the 2.7 version of Python and consequently to install all Python dependencies locally.

You can use the following script

.. code-block:: bash

  multipy install 2.7

to download, compile, and install python 2.7 into ``~/multipy`` directory.

To enable this local version, you have to call from your shell command line

.. code-block:: bash

  source ~/multipy/pythons/2.7/bin/activate

You can also add the previous line into ``.bashrc`` to activate your local
version of Python every time you start a bash console.

When you activate your local Python, you can install all python packages using ``pip`` or ``easy_install`` locally.
