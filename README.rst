.. image:: alex/doc/alex-logo.png
    :alt: Alex logo

Alex Dialogue Systems Framework
=================================================

..  image:: https://travis-ci.org/UFAL-DSG/alex.png
    :target: https://travis-ci.org/UFAL-DSG/alex

.. image:: https://readthedocs.org/projects/alex/badge/?version=latest&style=travis
    :target: https://readthedocs.org/projects/alex/?badge=latest
    :alt: Documentation Status

.. image:: https://landscape.io/github/UFAL-DSG/alex/master/landscape.png
   :target: https://landscape.io/github/UFAL-DSG/alex/master
   :alt: Code Health

Description
-----------------
The Alex Dialogue Systems Framework is named after `the famous parrot Alex <http://en.wikipedia.org/wiki/Alex_(parrot)>`_.

This framework is being developed by the dialogue systems group at UFAL - http://ufal.mff.cuni.cz/ -
the Institute of Formal and Applied Linguistics, Faculty of Mathematics and Physics, Charles University in Prague,
Czech Republic. The purpose of this work is to facilitate research into and development of spoken dialogue systems.

The main goals are:

- provide baseline components need for a building spoken dialogue systems (SDSs)
- provide example implementations of SDSs for several domains
- provide tools for processing dialogue system interactions logs, e.g. for audio transcription, semantic annotation,
  or SDSs evaluation

Implemented features:

- VOIP using ``PJSIP 2.1`` with some modifications
- ASR using ``GoogleASR``  or ``KALDI``
- VAD using Gaussian Mixure Models or Feed-Forward Neural Networks
- SLU using a set of logistic regression classifiers for detecting dialogue acts
- DM using probablistic discriminative dialogue state tracking and handcrafted policies
- NLG using template based generation possibly with efficient inflection into the correct surface form for
  morphologically rich languages
- TTS using ``flite``, ``VoiceRSS`` and ``SpeechTech``
- evaluation of dialogue systems using CrowdFlower crowdsourcing platform
- example dialogue domains:

  - PTIcs: :doc:`alex.applications.PublicTransportInfoCS.README`
  - PTIen: :doc:`alex.applications.PublicTransportInfoEN.README`

Features implemented in different repositories:

- transcription and semantic annotation of collected phone calls using the Crowdflower crowdsourcing platform: https://github.com/UFAL-DSG/django-crowdflower-annotations

Missing features:

- no user simulator for any of the supported domains
- no trainable dialogue policies

Installation
------------
Please follow the instructions provided in :doc:`INSTALL`.

Coding style
------------
This project follows the coding convention defined in PEP8. However, do not
automatically reformat the length of the lines. The *right* length of a line
is for every person different!

Development process
-------------------
Anyone can contribute to the project as long as he or she agrees to publish the contributions under the APACHE 2.0
license.

If you are a core member of the development team, please do not make changes directly in the master branch. Please,
make a topic branch and when you believe that your changes are completed and properly tested, update your branch from
master, and again *re-test the code*. Testing involves:

- evaluating the projects unittest using nose
- testing all interactive tests in the ``alex/test`` directory
- testing that the example dialogue domains are working properly. E.g.

  - running PTIcs: :doc:`alex.applications.PublicTransportInfoCS.README`
  - running RAMcs: :doc:`alex.applications.RepeatAfterMe.README`

If you are **not** a core member of the development team, please **fork** the project. Then make a topic branch make all
changes in the topic branch. Then follow the instructions above, that is:

- evaluate unit and interactive tests, test the implemented domains that they still work with your changes
- then merge any changes upstream in the master master branch
- again do the evaluation and testing
- if everything is ok, send us a pull request.

Documentation
-------------
The documentation is available `here <http://alex.readthedocs.org/en/latest/>`_ and is 
automatically generated after each push on readthedocs.org using Sphinx and its ``autodoc`` 
extension. Please document all your code as much as possible using the conventions which can 
be parsed by Sphinx. 

Also provide README style documentation describing the complete packages, applications, 
or preparation of data and models. The documentation should be placed near the code 
and/or application to which it is the most relevant. 
For formatting the text, use reStructured (reSt) *wiki like* syntax. 
The advantage of reSt is that it is fairly readable in source format 
and it can be nicely rendered into HTML or PDF using Sphinx. 
Documents with the ``rst`` extension are automatically detected, 
included into the documentation, and an index page for these documents is created.

Each document should start with a every descriptive title, e.g.:

::

  Description of building domain specific language model for the PTI domain
  =========================================================================

Then the text should be sectioned further, e.g.:

::

  Introduction
  ------------

  Evaluation
  -----------

  Notes
  -----

More information on  how to write documentation is available at

- `Quick cheatsheet for ReST and Sphinx <http://matplotlib.org/sampledoc/cheatsheet.html>`_
- `More thorough documentation with code examples <http://packages.python.org/an_example_pypi_project/sphinx.html>`_
- The docstrings should follow google (or sphinx or numpy) style. See examples: 
    - http://sphinxcontrib-napoleon.readthedocs.org/en/latest/#google-vs-numpy
    - http://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html#example-google


To compile and see the documentation, you can:

.. code-block:: bash

  $ cd doc
  $ make html

The open in your browser file ``doc/_build/html/index.html``.

If you need to completely rebuild the documentation, then run:

.. code-block:: bash

  $ make clean
  $ make html

You can build also a PDF file using the ``make latexpdf`` command.

License
-------
This code is released under the APACHE 2.0 license unless the code says otherwise and its license does not allow re-licensing.
The full wording of the APACHE 2.0 license can be found in the LICENSE-APACHE-2.0.TXT.

List of contributors
--------------------
If you contributed to this project, you are encouraged to add yourself here ;-)

- Filip Jurcicek
- Jan Hajic jr.
- Lukas Zilka
- Ondrej Dusek
- Matej Korvas
- David Marek
- Ondrej Platek
