
#!/usr/bin/python

# To run sanity check, run this line if scurl is in the current directory:
# /usr/class/cs255/bin/sanity/sanity $PWD/scurl

"""
to make it a shell command:
1) rename the file to just "scurl"
in directory, type:
chmod 755 scurl
now it works as a shell command
"""

# Tom Kremer
# Ben Krausz

import sys
from sys import argv, stdout
import socket
import re
import datetime
from urlparse import urlparse
import copy

from OpenSSL import SSL
from OpenSSL import crypto

"""
Things that are put on hold:
Comparing to list of trusted CAs
doesn't work for stanford.edu (related to www-aws?)
"""
url_object = {}

flagmap = {"--tlsv1.0": False,
	"--tlsv1.1": False,
	"--tlsv1.2": False,
	"--sslv3": False,
	"-3": False,
	"--ciphers": False,
	"--crlfile": False,
	"--cacert": False,
	"--allow-stale-certs": False,
	"pinnedcertificate": False}

def parse_args():
	print 'Number of arguments:', len(sys.argv), 'arguments.'
	print 'Argument List:', str(sys.argv)
	i = 0
	while(i < len(sys.argv)):
		if(sys.argv[i]=='--tlsv1.0'):
			flagmap['--tlsv1.0'] = True
			flagmap['--tlsv1.1'] = False
			flagmap['--tlsv1.2'] = False

		if(sys.argv[i]=='--tlsv1.1'):
			flagmap['--tlsv1.0'] = False
			flagmap['--tlsv1.1'] = True
			flagmap['--tlsv1.2'] = False

		if(sys.argv[i]=='--tlsv1.2'):
			flagmap['--tlsv1.0'] = False
			flagmap['--tlsv1.1'] = False
			flagmap['--tlsv1.2'] = True

		if(sys.argv[i]=='--sslv3'):
			flagmap['--sslv3'] = True

		if(sys.argv[i]=='-3'):
			flagmap['-3'] = True

		if(sys.argv[i]=='--cacert'):
			#NEED TO CONFIRM FILE IS VALID
			if(i+1 < len(sys.argv)):
				flagmap['--cacert']= sys.argv[i+1]
				i=i+2
				continue
			else:
				print "scurl: try 'scurl --help' or 'scurl --manual' for more information"
				return False

		if(sys.argv[i]=='--crlfile'):
			#NEED TO CONFIRM FILE IS VALID
			if(i+1 < len(sys.argv)):
				flagmap['--crlfile']=sys.argv[i+1]
				i=i+2
				continue
			else:
				print "scurl: try 'scurl --help' or 'scurl --manual' for more information"
				return False


		if(sys.argv[i]=='--pinnedcertificate'):
			#NEED TO CONFIRM FILE IS VALID
			if(i+1 < len(sys.argv)):
				flagmap['--pinnedcertificate']=sys.argv[i+1]
				i=i+2
				continue
			else:
				print "scurl: try 'scurl --help' or 'scurl --manual' for more information"
				return False

		if(sys.argv[i]=='--allow-stale-certs'):
			if(i+1 < len(sys.argv) and sys.argv[i+1].isdigit() and sys.argv[i+1]>=0):
				print 'allow stale certs by ' + sys.argv[i+1] + ' days'
				flagmap["--allow-stale-certs"]= sys.argv[i+1]
				i=i+2
				continue
			else:
				print '--allow-stale-certs invalid N'
				return False

		if(sys.argv[i]=='--ciphers'):
			#NEED TO CONFIRM CIPHERS ARE VALID
			if(i+1 < len(sys.argv)):
				flagmap['--ciphers']=sys.argv[i+1]
				i=i+2
				continue
			else:
				print "scurl: try 'scurl --help' or 'scurl --manual' for more information"
				return False
		else:
			print "scurl: try 'scurl --help' or 'scurl --manual' for more information"
			return False

		i=i+1
	print flagmap
	return True



def cb_func(conn, cert, errno, errdepth, ok):
	global url_object

	# Checking name on leaf certificate (doesn't work)

	""" 
	NOTES:
	Also it allows wildcards on any place which is against the rule that 
	wildcards should only be allowed in the leftmost label: *.example.com 
	is fine while www.*.com or even *.*.* is not allowed but accepted by your code.
	"""

	if errdepth == 0:
		
		pattern = copy.deepcopy(cert.get_subject().commonName)
		
		num_dots1 = cert.get_subject().commonName.count('.')
		num_dots2 = url_object['common_name'].count('.')
		if num_dots1 != num_dots2:
			# Wildcard character introduced new periods, which isn't allowed
			return False
		if pattern.rfind('*') > pattern.find('.'):
			# Asterisk not in left section
			return False
		
		pattern = pattern.replace('.', r'\.').replace('*', r'.*')
		# print url_object['common_name']
		# print pattern
		if not re.match(pattern, url_object['common_name']):
			return False		

	# if errdepth == 0:
	# 	regex = cert.get_subject().commonName.decode().replace('.', r'\.').replace('*',r'.*') + '$'
		# print regex
	# 	if re.match(regex, url):
	# 	if cert.get_subject().commonName != url:
			# print "Certificate name doesn't match host"
			# return False

	if (errno == 9 or errno == 10):
		# print "Not in valid time"
		return False
	# else:
		# print "Valid time"

	# start_date = int(cert.get_notBefore()[:-1])
	# exp_date = int(cert.get_notAfter()[:-1])
	# now = int(datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"))
	# if not (start_date < now < exp_date):
	# 	print "Not in valid time"
	# 	# THROW ERROR HERE!
	# 	return False
	# else:
	# 	print "Valid time :)"

	return ok


"""
Constructs a parsed url
url_object = {
	common_name: "www.google.com",
	port: 443 (int)
	path: '/path'
}
Returns none if invalid url type
"""
def parse_url(url):
	global url_object	

	if url.startswith('//'):
		url = 'https:' + url

	if url.startswith('http://'):
		url = url[:4] + 's' + url[4:]

	if not url.startswith('https://'):
		url = "https://" + url
	
	parsed_url = urlparse(url)
	# ParseResult(scheme='http', netloc='www.cwi.nl:80', path='/%7Eguido/Python.html',
    #        params='', query='', fragment='')
	# print parsed_url

	if len(parsed_url.netloc) > 0:
		if ":" in parsed_url.netloc:
			index = parsed_url.netloc.find(":")
			url_object['common_name'] = parsed_url.netloc[:index]
			url_object['port'] = int(parsed_url.netloc[index+1:])
		else:
			url_object['common_name'] = parsed_url.netloc
			url_object['port'] = 443

		# Path is just everything after the common name and/or port
		url_object['path'] = url.split(parsed_url.netloc)[1]
		if len(url_object['path']) == 0:
			url_object['path'] = '/'
	else:
		return False

	return True

"""
Sets up the socket, context, and connection.
Returns a conenction object
"""
def establish_connection(url_obj, tls_v):
	# Setting up socket, context, and connection
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	myContext = SSL.Context(tls_v)

	myContext.set_verify(SSL.VERIFY_PEER|SSL.VERIFY_FAIL_IF_NO_PEER_CERT, cb_func)
	myContext.set_default_verify_paths()
	
	"""
	Context.set_cipher
	"""

	myConnection = SSL.Connection(myContext, sock)

	myConnection.set_tlsext_host_name(url_obj['common_name'])
	myConnection.set_connect_state()

	myConnection.connect((url_obj['common_name'], url_obj['port']))

	return myConnection


def main():
	global url_object

	url = "www.facebook.com"
	worked = parse_url(url)
	if not worked:
		# "Badly formatted url"
		return

	myConnection = establish_connection(url_object, SSL.TLSv1_METHOD)
	if myConnection is None:
		# print "Couldn't establish connection ???? "
		return

	try:
		myConnection.do_handshake()
	except (SSL.ZeroReturnError, SSL.Error):
		# print "Invalid certificate"
		return

	# print "Connection established"

	# print myConnection.state_string()

	#myContext.set_options()

	# The browser checks that the certificate was issued by a trusted party 
	# (usually a trusted root CA), that the certificate is still valid and 
	# that the certificate is related to the site contacted.
	myConnection.sendall("GET " + url_object['path'] + " HTTP/1.1\r\nHost: " + url_object['common_name'] + "\r\nUser-Agent: Tom and Ben\r\n\r\n") # HTTP/1.1

	t1 = []
	try:
		numBytes = 1024
		while True:
			r = myConnection.recv(numBytes)
			t1.append(r)
			if len(r) < numBytes and "</html>" in r:
				# print "DONE getting HTML"
				break
	except (SSL.ZeroReturnError, SSL.Error):
		pass



	myConnection.shutdown()
	myConnection.close()
	html_string = "".join(t1)
	# print html_string
	html_body_index = html_string.find('<!DOCTYPE html>')
	if html_body_index == -1:
		html_body_index = html_string.find('<!doctype html>')
	html_body = html_string[html_body_index:]
	print html_body
	parse_args()



if __name__ == "__main__":
	main()