OLD -Installation instructions
=========================

Local python
------------

At this moment, the SDS project is developed and tested in Python 2.7.

To make sure that you can install all required packages it is better to
have your own locally compiled version of python.

You can use the following script::

  SDS/thirdparty/akheron-multipy/multipy install 2.7

to download, compile, and install python 2.7 into ``~/multipy`` directory.

To enable this local version, you have to call from your bash command line::

  source ~/multipy/pythons/2.7/bin/activate

You can also add the previous line into ``.bashrc`` to activate your local
version of python every time you start a bash console.

Dependencies
------------

Ubuntu 12.04
~~~~~~~~~~~~

If you are root on the computer, then run::

    sudo apt-get install gfortran libatlas-base-dev portaudio19-dev flac \
        speex sox mplayer libsqlite3-dev python-numpy python-scipy \
        python-wxgtk2.8 python-matplotlib python-sklearn python-Levenshtein \
        python-pymad python-pysqllite2

To get latest versions of some python packages, I recomend to run these
commands::

    sudo pip install --upgrade numpy
    sudo pip install --upgrade scipy
    sudo pip install --upgrade matplotlib
    sudo pip install boto

Ubuntu 10.04
~~~~~~~~~~~~

Install the following packages:

fortran

* ::

    $ sudo apt-get install gfortran

atlas

- install ATLAS libraries to get fast linear algebra support::

    $ sudo apt-get install libatlas-base-dev

- If you need optimised ATLAS and LAPACK libraries then you have to compile
  them on your own. Then modify config for numpy. Optimised ATLAS and LAPACK
  can compute matrix multiplication on all cpu cores available.

  To build your own optimised ATLAS and LAPACK libraries:

  - get latest LAPACK
  - get latest ATLAS
  - compile lapack
  - tell atlas where is your compiled LAPACK
  - compile ATLAS

flac

* ::

    $ sudo apt-get install flac

sqllite3

* ::

    $ sudo apt-get install libsqlite3-dev

When having your own compiled version of python then remember that sometimes you have to recompile the Python installation when
adding packages or modules, e.g. when ``libsqlite3-dev`` is installed.

Local versions of Python packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most of the packages are in ``SDS/thirparty/installable`` to provide packages
the SDS is tested with.

numpy

* download latest numpy
* unpack
* got to main directory
* tell numpy where is atlas and lapack if you have your own compiled
* run::

    $ python setup.py install

scipy

- download latest scipy
- unpack
- got to main directory
- run::

    $ python setup.py install

scikit-learn

* ::

  $ easy_install scikit-learn

python-Levenshtein

* ::

  $ easy_install python-Levenshtein

pyAudio

- get a special version from https://github.com/bastibe/PyAudio
  (bastibe-PyAudio-2a08fa7)
- this version supports non-blocking audio
- run::

    $ python ./setup.py install

pymad

* ::

  $ easy_install pymad

pysqllite

* ::

  $ easy_install pysqlite

Source compiled packages
~~~~~~~~~~~~~~~~~~~~~~~~

flite

- get the latest flite
- build flite::

    $ bunzip2 flite-1.4-release.tar.bz2
    $ tar -xvf flite-1.4-release.tar
    $ cd flite-1.4-release
    $ ./configure
    $ make

- put ``flite-1.4-release/bin/flite`` into you search path.
  E.g. link the flite program to your bin directory

pjsip

- get the latest pjsip
- build pjsip::

    $ bunzip2 pjproject-2.0.tar.bz2
    $ tar -xvf pjproject-2.0.tar
    $ cd pjproject-2.0
    $ ./configure CXXFLAGS=-fPIC CFLAGS=-fPIC LDFLAGS=-fPIC CPPFLAGS=-fPIC
    $ make dep
    $ make
    $ make install

- install python pysuaxt
- copy or simply link the following files from directory 
  ``SDS/thirdparty/installable/py_pjsuaxt``::

    _pjsuaxt.c
    _pjsuaxt.def
    _pjsuaxt.h
    pjsuaxt.py
    setup-pjsuaxt.py

  to the directory ``(your-path)/pjproject-2.0/pjsip-apps/src/python/``
  then go to that directory ``(your-path)/pjproject-2.0/pjsip-apps/src/python/`` and run::

    $ python setup-pjsuaxt.py install

  this will install extended pjsua library which support in memory playing and recording of calls

HTK

- get the latest HTK (3.4.1 tested) from http://htk.eng.cam.ac.uk/download.shtml
- build and install the HTK

SRILM

- get the latest SRILM (1.6 tested) from http://www.speech.sri.com/projects/srilm/
- build and install the SRILM

Julius

- get the latest Julius ASR decoder (4.2.2 tested - 4.2.1 generates seg faults) from http://julius.sourceforge.jp/en_index.php
- build and install

Optional packages
~~~~~~~~~~~~~~~~~

wxpython

* ::

    pip install wxpython

matplotlib

* ::

    pip install matplotlib

boto

* ::

    pip install boto