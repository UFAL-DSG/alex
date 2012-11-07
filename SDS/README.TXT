Simple (spoken) Dialogue System  (SDS)

= INSTALL =

== Local python ==
At this moment, the SDS project is developped and tested in Python 2.7.

To make sure that you can install all requeried packages it is better to have your own locally compiled version of python.

You can use the following script

  ./thirdparty/akheron-multipy/multipy install 2.7

to download, compile, and install python 2.7 into ~/multipy directory.

To enable this local version, you have to call from your bash commandline

  source ~/multipy/pythons/2.7/bin/activate

You can also add the previous line into .bashrc to activate your local version of python everytime you start a bash console.

== Dependecies ==

Please follow ./thirdparty/DEPENDENCIES.TXT to install all necessary pakages.
Some packages are included in there so that you can use the versions which are used by this project.

= CODING STYLE =

This project follows coding convection defined in PEP8.

