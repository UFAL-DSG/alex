#!/bin/bash
#MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../../" && pwd )"

#TODO: docker acquire czech, checkout english, provide additional stuff and start docker with -v for english sources
#BASE_FOLDER=${CURDIR}
BASE_FOLDER=/mnt/data
SOURCE_FOLDER=${BASE_FOLDER}/alex

SRC_VOLUME="-v ${SOURCE_FOLDER}:/app/alex"
DOCKER_OPTS="--rm -i -t ${SRC_VOLUME}"

docker run ${DOCKER_OPTS} ptien /bin/bash


# Run an interactive shell in the ubuntu image,
# allocate a tty, attach stdin and stdout
# To detach the tty without exiting the shell,
# use the escape sequence Ctrl-p + Ctrl-q
# note: This will continue to exist in a stopped state once exited (see "docker ps -a")
# sudo docker run -i -t ubuntu /bin/bash