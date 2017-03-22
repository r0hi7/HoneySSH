#!/usr/bin/python3

import requests
import json
from sys import argv
import os
import time
import elasticsearch

# if not os.path.isfile('api_key.config'):
# 	#api_key = raw_input('Enter your private api key:')
# 	with open("api_key.config","a+") as f:
# 		f.write(api_key)
# 	f.close()
# else:
# 	f = open("api_key.config","r")
# 	api_key = f.read()
# 	f.close()

api_key = '360287c5282c4ea0e1022687e0a5114e06ef80cf00b49b806dde8d04d7e75398'
params = {'apikey': api_key}
textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))

#onlyfiles = [f for f in os.listdir(".") if os.path.isfile(os.path.join(".", f))]
src,file_name = argv

#for file_name in onlyfiles:
if is_binary_string(open(file_name, 'rb').read(1024)):
	analysis_file = "VT-"+file_name
	#if not os.path.isfile(analysis_file):
	files = {'file': (file_name, open(file_name, 'rb'))}
	response = requests.post('https://www.virustotal.com/vtapi/v2/file/scan', files=files, params=params)
	json_response = response.json()
	md5 = json_response['md5']
	time.sleep(20)
	params = {'apikey': api_key, 'resource': md5}
	headers = {"Accept-Encoding": "gzip, deflate","User-Agent" : "gzip,  My Python requests library example client or username"}
	response = requests.get('https://www.virustotal.com/vtapi/v2/file/report',params=params, headers=headers)
	json_response = response.json()
	del json_response['scan_id']
	del json_response['sha1']
	del json_response['resource']
	del json_response['response_code']
	del json_response['scan_date']
	del json_response['permalink']
	del json_response['verbose_msg']
	del json_response['sha256']
	json_response['name'] = file_name
	f = open(analysis_file, "a+")
	#arr = json.dumps(json_response,f)
	json.dump(json_response,f)
	f.close()
	es = elasticsearch.Elasticsearch()
	es.index(index='vt',doc_type='log', body=json_response)
	#print(rep)
	#obj = json.loads(arr)
	#f = open(analysis_file,"a+")
	#for i in obj:
	#	f.write(i)
	#	f.write("-")
	#	f.write(obj[i]['result'])
	#	f.write("\n")
	#f.close()
	#time.sleep(20)
