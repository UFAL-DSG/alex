Online distribution of resource files such as ASR, SLU, NLG models
==================================================================

Large binary files are difficult to store in git. Therefore, files such as resource files for ASR, SLU or NLG
are distributed online and on-demand.

To use this functionality you have to use the ``online_update(file_name)`` function from the ``alex.utils.config`` package.
The functions checks the file name whether it exists locally and it is up-to-date. If it is missing or it is old, then
a new version from the server is downloaded.

The function returns name if the downloaded file which equal to input file name. As a result it is transparent in a way,
that this function can be used everywhere a file name must be entered.

The server is set to ``https://vystadial.ms.mff.cuni.cz/download/``; however, it can be changed using the
``set_online_update_server(server_name)`` function from inside a config file, e.g. the (first) default config file.



