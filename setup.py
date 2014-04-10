from setuptools import setup, find_packages
from os import path


long_description = open(path.join(path.dirname(__file__), 'README.rst')).read()


setup(
    name='Alex Dialogue System Framework',
    packages=find_packages(),
    version='0.1',
    test_suite="nose.collector",
    author='UFAL-DSG https://github.com/UFAL-DSG/',
    author_email='dsg-l@ufal.mff.cuni.cz',
    url='https://github.com/DSG-UFAL/alex',
    license='Apache, Version 2.0',
    keywords='Alex Spoken Dialogue System Framework Public Transport Domain UFAL MFF',
    description='Framework for developing Dialogue systems',
    long_description=long_description,
    classifiers='''
        Programming Language :: Python :: 2
        License :: OSI Approved :: Apache License, Version 2
        Operating System :: POSIX :: Linux
        Intended Audiance :: Dialogue System scientist
        Intended Audiance :: Students
        Environment :: Console
        '''.strip().splitlines(),
)
