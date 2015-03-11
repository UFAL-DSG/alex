Public Transport Info, English - telephone service
============================================================

Running the system at UFAL with the full UFAL access
----------------------------------------------------

There are multiple configuration that can used to run the system. 
In general, it depends on what components you want go use and
on what telephone extension you want to run the system.

Within UFAL, we run the system using the following commands:

- ``vhub_mta1`` - deployment of our live system on a 1-855-528-7350 phone number, with the default configuration
- ``vhub_mta2`` - a system deployed to backup the system above
- ``vhub_mta3`` - a system deployed to backup the system above
- ``vhub_mta_btn`` - a system deployed to backup the system above accessible via web page http://alex-ptien.com

To test the system we use:

- ``vhub_devel`` - default devel version of our system deployed on our test extension, logging locally into ``../call_logs``


Running the system without the full UFAL access
-------------------------------------------------------

Users outside UFAL can run the system using the following commands:

- ``vhub_private_ext_google_only_hdc_slu`` - default version of our system deployed on private extension specified in ``private_ext.cfg``, using HDC_SLU, Google ASR, TTS, Directions, logging locally into ``../call_logs``
- ``vhub_private_ext_google_kaldi_hdc_slu`` - default version of our system deployed on private extension specified in ``private_ext.cfg``, using HDC_SLU, Google TTS, Directions, and KALDI ASR, logging locally into ``../call_logs``

If you want to test the system on your private extension, then modify the ``private_ext.cfg`` config. You must set your
SIP domain including the port, user login, and password. Please make sure that you do not commit your login information
into the repository.

:: 

    config = {
            'VoipIO': {
                    # default testing extesion
                    'domain':   "*:5066",
                    'user':     "*",
                    'password': "*",
            },
    }

Also, you will have to create a "private" directory where you can store your private configurations.
As the private default configuration is not part of the Git repository, please make your own empty version of 
the private default configuration as follows.

:: 
    
    mkdir alex/resources/private
    echo "config = {}" > alex/resources/private/default.cfg
    

    
