This directory contains two types of tests:

* unit tests
* tests, which can't be automated


There are two ways how to run unit tests:

1. Using unittest module:

        $ python -m unittest SDS.test.test_string

    This approach works everywhere but doesn't support test discovery.

2. Using nose test discovery framework.

        $ easy_install nose
        $ nosetests

    Nose searchs through packages and runs every test. Tests must be
    named test_<something>.py and must not be executable.


How should my unit tests look like?

* Use unittest module
* Name the test file test_<something>.py
* Make the test file not executable