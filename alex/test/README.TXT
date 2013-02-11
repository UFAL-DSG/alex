This directory contains only tests, which can't be automated and the results must verified by humans!


Note that the unit tests should be placed in the same diractory as the tested module and the name shoud be test_*.py e.g. test_module_name.py

1. Using unittest module:

				$ python -m unittest alex.test.test_string

    This approach works everywhere but doesn't support test discovery.

2. Using nose test discovery framework.

        $ easy_install nose
        $ nosetests

    Nose searchs through packages and runs every test. Tests must be named
    test_<something>.py and must not be executable. Tests doesn't have to be
    run from project root, nose is able to find project root on its own.


How should my unit tests look like?

* Use unittest module
* Name the test file test_<something>.py
* Make the test file not executable
