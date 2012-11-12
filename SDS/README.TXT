Simple (spoken) Dialogue System  (SDS)

= INSTALL =

== Local python ==
At this moment, the SDS project is developed and tested in Python 2.7.

To make sure that you can install all required packages it is better to 
have your own locally compiled version of python.

You can use the following script

  ./thirdparty/akheron-multipy/multipy install 2.7

to download, compile, and install python 2.7 into ~/multipy directory.

To enable this local version, you have to call from your bash command line

  source ~/multipy/pythons/2.7/bin/activate

You can also add the previous line into .bashrc to activate your local 
version of python every time you start a bash console.

== Dependencies ==

Please follow ./thirdparty/DEPENDENCIES.TXT to install all necessary 
packages.
Some packages are included in there so that you can use the versions which 
are used by this project.

= CODING STYLE =

This project follows the coding convention defined in PEP8.

