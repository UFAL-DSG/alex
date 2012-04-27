Simple (spoken) Dialogue System  (SDS)

= INSTALL =

== Local python ==
To make sure that you can install all requeried packages it is better to have your own locally compiled version of python.
At this moment, the SDS project is developped and tested in Python 2.7.

You can use the following script 

  ./thirdparty/akheron-mutipy/multipy install 2.7

to download, compile, and install python 2.7 into ~/multipy directory.

To enable this local version, you have to call froum your bash commandline 

  source ~/multipy/pythons/2.7/bin/activate
  
You can also add the previous line into .bashrc to activate your local version of python everytime you start a bash console.

== Add support for absolute import of SDS ==
 
You must add the directory which contains SDS into PYTHONPATH shell variable.
E.g.

    export PYTHONPATH=$PYTHONPATH:/../where-is-your-sds-dir-placed/


Or you can link to that directory from your local site-packages directory.

E.g. the directory containing you local python and site packages

  ~/multipy/pythons/2.7/lib/python2.7/site-packages

will contain a sym link SDS directing to the directory where the SDS project is stored.

(2.7)jurcicek@loki:/.../multipy/pythons/2.7/lib/python2.7/site-packages$ ll
total 232
drwxr-xr-x 4 jurcicek ufal   4096 2012-01-30 12:45 distribute-0.6.24-py2.7.egg
-rw-r--r-- 1 jurcicek ufal    215 2012-01-30 12:45 easy-install.pth
-rwxr-xr-x 1 jurcicek ufal 209433 2012-01-30 13:03 Levenshtein.so
drwxr-xr-x 2 jurcicek ufal   4096 2012-01-30 13:03 python_Levenshtein-0.10.2-py2.7.egg-info
-rw-r--r-- 1 jurcicek ufal    119 2012-01-30 12:44 README
lrwxrwxrwx 1 jurcicek ufal     49 2012-01-30 15:32 SDS -> /.../SDS
-rw-r--r-- 1 jurcicek ufal    144 2012-01-30 12:45 setuptools-0.6c11-py2.7.egg-info
-rw-r--r-- 1 jurcicek ufal     34 2012-01-30 12:45 setuptools.pth

== Dependecies ==

Please follow ./thirdparty/DEPENDENCIES.TXT to install all necessary pakages. 
Some packages are included in there so that you can use the versions which are used by this project.

= CODING STYLE = 

This project follows coding convection defined in PEP8.

