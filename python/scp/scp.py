#!/usr/bin/env  python
# -*- coding: utf-8 -*-
'''
Description: This script reads sensor values and runtime information.
It pushes data to preconfigured devices on the SAP IoT Leonardo Foundation.

IoT Services 4.0 (CF)

Some dependencies need to be installed before running this script.
Please ensure to install following libraries prior to the first execution.
- OpenSSL
- requests

Author: Robin Rosner, SAP Deutschland SE
Forked from 'https://github.com/SAP/iot-starterkit'
'''

import sys, requests, shlex, subprocess, json, time, os, math, RPi.GPIO as GPIO


# Enter your IoT Services device configuration
_certfile_name					= "cert.pem"

_bootTimeScript					= time.time()
_sendInterval 					= 5
_connectionTimeout				= 30
_retryTimer						= 2

# Bypass Proxy set on Images (http://piproxy.fair.sap.corp:8080)
# Comment the following line if you are located in SAP-Guest network
#os.environ['NO_PROXY'] = _instance


# Post measurements to IoT Services 4.0 instance
def postIoTService(deviceAltId, capabilityAltId, sensorAltId, measures, description = ""):
	postAddress	= "https://" + _instance + "/iot/gateway/rest/measures/" + deviceAltId
	headers = {'content-type': 'application/json'}
	data = json.dumps({"capabilityAlternateId": capabilityAltId, "sensorAlternateId": sensorAltId, "measures":measures})
	#print("==> Posting %s: %s" % (description, data))
	try:
		r = requests.post(postAddress,data=data, headers = headers, cert=(_certfile_name, _keyfile_name), timeout=_connectionTimeout)
		#print ("==> HTTP Response Code: %d\n" %r.status_code)
		if not (r.status_code == 200):
			print ("%s" %r.text)
	except requests.exceptions.Timeout:
		return False
    # Maybe set up for a retry, or continue in a retry loop
	except requests.exceptions.RequestException as e:
	    print e
	    sys.exit(1)
	return True

# Get and save device certificate
def getDeviceCertificate(user, pw, deviceIdParam, deviceAlternateId):
	request_url='https://' + _instance + '/iot/core/api/v1/devices/' + deviceIdParam + '/authentications/clientCertificate/pem'	
	headers={'Content-Type' : 'application/json'}
	#print ("==> Getting Device Certificate")
	#print request_url;
	r=requests.get(request_url, headers=headers, auth=(user, pw), timeout=_connectionTimeout)
	#print ("==> HTTP Response Code: %d" %r.status_code)
	if (r.status_code == 200):
		try:
			json_payload=json.loads(r.text)
			secret=json_payload['secret']
			pem=json_payload['pem']
			certfile=open(_certfile_name, "w")
			certfile.write(pem)
			certfile.close()
			#print ("==> Certificate downloaded successfully")
			convertPemFile(json_payload['secret'], deviceAlternateId)
		except (ValueError) as e:
	                print(e)
	else:
		#print ("==> HTTP Response Payload: %s" %r.text)
		sys.exit(r.status_code)

# Convert password encrypted PEM to RSA-encrypted PEM
def convertPemFile(sec, deviceAlternateId):
	dr = os.path.dirname(os.path.realpath(__file__))
	#print ("==> Converting certificate")
	if not os.path.isfile(_certfile_name):
		#print("Certificate '" + _certfile_name + "' not found")
		sys.exit(0)
	s = "openssl rsa -in " + os.path.join(dr, _certfile_name) + " -passin pass:" + sec + " -out " + os.path.join(dr, _keyfile_name)
	out, err = subprocess.Popen(shlex.split(s), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
	if not (err.strip() == "writing RSA key"):
		print("Error during conversion")
		sys.exit(1)
	#print("Conversion to RSA-Keyfile '%s' successful\n" %_keyfile_name)
	#os.system("openssl x509 -in " + _certfile_name + " -out credentials.crt\n")


try:
	_instance						= sys.argv[1]
	user							= sys.argv[2]
	pw								= sys.argv[3]
	deviceId 						= sys.argv[4]
	deviceAlternateId 				= sys.argv[5] 
	sensorAlternateId 				= sys.argv[6]
	_capabilityAlternateId			= sys.argv[7]
	measure							= sys.argv[8]
	_keyfile_name					= "certificate{}.key".format(deviceAlternateId)
	
	#print 'Argument List:', str(sys.argv)
	
	#print("==> Testing connection")
	if not os.path.isfile(_keyfile_name):
		#print ("==> Keyfile not found")
		getDeviceCertificate(user, pw, deviceId, deviceAlternateId)

	while not postIoTService(deviceAlternateId, _capabilityAlternateId, sensorAlternateId, [measure], "Sensordata"):
		
		time.sleep(_retryTimer)
except KeyboardInterrupt:
	os.remove(_keyfile_name)
	sys.exit(0)
