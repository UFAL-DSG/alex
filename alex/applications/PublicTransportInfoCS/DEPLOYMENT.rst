Public Transport Info, Czech - telephone service
============================================================

Running the system at UFAL with the full UFAL access
----------------------------------------------------

There are multiple configuration that can used to run the system. 
In general, it depends on what components you want go use and
on what telephone extension you want to run the system.

Within UFAL, we run the system using the following commands:

- ``vhub_live`` - deployment of our live system on our toll-free phone number, with the default configuration
- ``vhub_live_b1`` - a system deployed to backup the system above
- ``vhub_live_b2`` - a system deployed to backup the system above
- ``vhub_live_kaldi`` - a version of our live system explicitly using Kaldi ASR

To test the system we use:

- ``vhub_test`` - default test version of our system deployed on our test extension, logging locally into ``../call_logs``
- ``vhub_test_google_only`` - test version of our system on our test extension, using Google ASR, TTS, Directions, logging locally into ``../call_logs``
- ``vhub_test_google_kaldi`` - test version of our system on our test extension, using Google TTS, Directions, and Kaldi ASR, logging locally into ``../call_logs``
- ``vhub_test_hdc_slu`` - default test version of our system deployed on our test extension, using HDC SLU, logging locally into ``../call_logs``
- ``vhub_test_kaldi`` - default test version of our system deployed on our test extension, using KALDI ASR, logging locally into ``../call_logs``
- ``vhub_test_kaldi_nfs`` - default test version of our system deployed on our test extension, using KALDI ASR and logging to NFS


Running the system without the full UFAL access
-------------------------------------------------------

Users outside UFAL can run the system using the following commands:

- ``vhub_private_ext_google_only`` - default version of our system deployed on private extension specified in ``private_ext.cfg``, using Google ASR, TTS, Directions, and KALDI ASR, logging locally into ``../call_logs``
- ``vhub_private_ext_google_kaldi`` - default version of our system deployed on private extension specified in ``private_ext.cfg``, using Google TTS, Directions, and KALDI ASR, logging locally into ``../call_logs``

If you want to test the system on your private extension, then modify the ``private_ext.cfg`` config. You must set your
SIP domain including the port, user login, and password (You can obtain a free extension at http://www.sipgate.co.uk).
Please make sure that you do not commit your login information into the repository.

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
    

    
