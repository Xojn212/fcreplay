#!/bin/bash
# Look for arguments
function help() {
    echo "No argument supplied. Use one of 'record', 'replay', 'tasker', or 'validate'"
    exit 1
}

function fcrecord() {
    Xvfb -screen :0 1024x768x16 > /dev/null 2>&1 &
    sleep 1
    export DISPLAY=:0
    export WINEDEBUG=-all
    i3 > /dev/null 2>&1 &
    tail -f /root/fcreplay.log
    #x11vnc > /dev/null 2>&1
}

function fcvalidate() {
    cd /root
    fcreplayvalidate $@
}

function fcreplay() {
    cd /root
    fcreplayget $@
}

function fctasker() {
    cd /root
    fcreplaytasker $@
}

if [ $# -eq 0 ]; then
    help
fi

# Look for the first argument
case $1 in
  record)
    fcrecord
    ;;

  replay)
    fcreplay ${@:2}
    ;;
  
  tasker)
    fctasker ${@:2}
    ;;

  validate)
    fcvalidate ${@:2}
    ;;

  *)
    help 
    ;;
esac