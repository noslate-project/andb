#!/bin/bash

_f=$BASH_SOURCE
echo $_f
SHELL_FOLDER=$(dirname "$_f")

pathadd() {
    if [ -d "$1" ] && [[ ":$PATH:" != ":$1:"* ]]; then
        export PATH=$1:$PATH
    fi
}

ROOT=$(cd "$SHELL_FOLDER"; pwd)
#pathadd $ROOT/usr/bin

#source /opt/rh/devtoolset-7/enable

alias andb=" $ROOT/loader"

echo "andb loader enabled, please use 'andb' command to start debugging."

