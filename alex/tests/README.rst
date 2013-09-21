Interective tests and unit tests
================================

Testing of Alex can be divided into interactive tests, which depends on on some activity of a user e.g. calling a
specific phone number or listening to some audi file, and unit tests, which are testing some very specific properties
of algorithms or libraries.

Interactive tests
-----------------

This directory contains only (interactive) tests, which can't be automated and the results must be verified by humans!
E.g. playing or recording audio, testing VOIP connections.


Unit tests
----------

Note that the unit tests should be placed in the same directory as the tested module and the name should be ``test_*.py``
e.g. ``test_module_name.py``.

Using unittest module:

::

  $ python -m unittest alex.test.test_string

This approach works everywhere but doesn't support test discovery.

Using nose test discovery framework, testing can largely automated.
Nose searchs through packages and runs every test. Tests must be named
``test_<something>.py`` and must not be executable. Tests doesn't have to be
run from project root, nose is able to find project root on its own.

How should my unit tests look like?

* Use unittest module
* Name the test file ``test_<something>.py``
* Make the test file not executable
