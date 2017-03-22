#!/bin/bash

file_name=`cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1`

wget $4 -o $file_name

python3 getInfo.py $file_name



