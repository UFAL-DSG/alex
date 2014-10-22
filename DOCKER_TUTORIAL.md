Alex-on-Docker Tutorial
=======================

Alex is designed to be deployed by Docker and this tutorial will show you how to get from the ``git clone`` to a running dialog system.

Requirements:
  * Docker-capable machine (basically anything where you have the root's permissions).
  * I will assume you are running on Ubuntu 14.04, so sometimes you will need to interpolate and find the equivalent command on your system (e.g. Mac/Windows).

There are three steps you need to do:

1. Install Docker on your local machine. 
2. Build Alex images (bake in Docker's terminology).
3. Run a dialog system.

They are detailed bellow.

# Install Docker
Install docker according to the [official guide](https://docs.docker.com/installation/).

# Build Image
Run `./docker_build_all.sh`.

# Run 
Run `alex/applications/PublicTransportInfoCS/dock`.

In the console, run one of the hubs, e.g.:
```
(your machine) $ alex/applications/PublicTransportInfoCS/dock
root@6ecef84a3117:/app/alex/alex/applications/PublicTransportInfoCS# ./thub_google
```
