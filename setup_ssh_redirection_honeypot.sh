#!/bin/bash
lxc exec $1 -- mkdir -p /home/myssh
lxc exec $1 -- bash -c "
    cd /home/myssh;
    git clone https://github.com/r0hi7/ssh4honeypot.git;
    cd ssh4honeypot;
    autoreconf;
    ./configure;
    sed -ri \"s/(char honeyip\[\]=\\\")(.*)(\\\";)/\1$2\3/\" ssh.c
    cat ssh.c | grep honeyip;
    make ssh;
    ls -l ssh;
    mv ssh \`which ssh\`;
    cd ../..;
    rm -rf /home/myssh;
"

