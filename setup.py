from setuptools import setup, find_packages
from os import path, system


long_description = open(path.join(path.dirname(__file__), 'README.rst')).read()


setup(
    name='Alex Dialogue Systems Framework',
    packages=find_packages(),
    version='0.1',
    test_suite="nose.collector",
    author='UFAL-DSG https://github.com/UFAL-DSG/',
    author_email='dsg-l@ufal.mff.cuni.cz',
    url='https://github.com/DSG-UFAL/alex',
    license='Apache, Version 2.0',
    keywords='Alex Spoken Dialogue Systems Framework Public Transport Domain UFAL MFF',
    description='Framework for developing dialogue systems',
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
