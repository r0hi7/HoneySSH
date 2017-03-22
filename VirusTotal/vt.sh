#!/bin/bash

file_name=`python -c 'import random;import string;print "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))'`

wget $4 -O VirusTotal/$file_name

python3 VirusTotal/getInfo.py VirusTotal/$file_name



