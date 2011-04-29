#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import hashlib
import urllib2
import json
import os
from BeautifulSoup import BeautifulStoneSoup

from getpass import getpass
from textwrap import TextWrapper
import pynotify
import tweepy


g_config_filename = u'./config.txt'
g_config = None

def decodehtmlentities(data):
	return unicode(BeautifulStoneSoup(data, convertEntities=BeautifulStoneSoup.HTML_ENTITIES))

def notify_gnome(title, msg, icon=None):
	pynotify.Notification(title, msg, icon).show()

def download(url, filename):
	data=urllib2.urlopen(url).read()
	open(filename, u'w').write(data)

def get_image(url):
	hashed = hashlib.sha1(url).hexdigest()
	filename = u'%s/cache/%s' % (os.getcwd(), hashed)
	try:
		open(filename).close()
	except IOError:
		print u'* Downloading %s as %s' % (url, filename)
		download(url, filename)
		open(u'./cache/list.txt', u'a').write(u'%s\t%s\n' % (hashed, url))
	
	return filename

tweetlogfile = open(u'./tweets.txt', u'a')

class StreamWatcherListener(tweepy.StreamListener):

	status_wrapper = TextWrapper(width=60, initial_indent=u'    ', subsequent_indent=u'    ')
	
	def on_data(self, data):
		super(StreamWatcherListener, self).on_data(data)
		tweetlogfile.write(data)
		tweetlogfile.write(u'\n')
		tweetlogfile.flush()

	def on_status(self, status):
		try:
			etcinfo = u'%s  %s  via %s' % (status.author.screen_name, status.created_at, status.source)
			profile_image = get_image(status.author.profile_image_url)
		except AttributeError:
			# sometimes status update lacks `author' key
			return
		
		print self.status_wrapper.fill(status.text)
		print u'\n %s\n' % etcinfo
		
		statustext = decodehtmlentities(status.text)
		etcinfo = decodehtmlentities(etcinfo)
		
		notify_gnome(statustext, etcinfo, profile_image)
		#notify_gnome(etcinfo, statustext, profile_image)

	def on_error(self, status_code):
		print u'An error has occured! Status code = %s' % status_code
		return True  # keep stream alive

	def on_timeout(self):
		print u'timeout'

def loadcfg():
	global g_config
	g_config = json.load(open(g_config_filename))
	#g_config = dict(map(lambda x: (str(x[0]), str(x[1])), g_config.iteritems()))
def savecfg():
	global g_config
	json.dump(g_config, open(g_config_filename, u'w'))

def main():
	global g_config
	loadcfg()
	
	auth = tweepy.OAuthHandler(g_config[u'consumer_key'], g_config[u'consumer_secret'])
	if u'access_token_key' not in g_config:
		try:
			redirect_url = auth.get_authorization_url()
		except tweepy.TweepError as e:
			print u'Error! Failed to get request token.'
			print(e)
		else:
			print(u'Authorization URL: %s' % redirect_url)
			pincode = raw_input(u'enter PIN code: ')
			auth.get_access_token(pincode)
			print(u'Key: %s' % auth.access_token.key)
			print(u'Secret: %s' % auth.access_token.secret)
			
			g_config[u'access_token_key'] = auth.access_token.key
			g_config[u'access_token_secret'] = auth.access_token.secret
			savecfg()

			print(u'OK. Now restart the program.')
		
		return
	else:
		auth.set_access_token(g_config[u'access_token_key'], g_config[u'access_token_secret'])
	
	stream = tweepy.Stream(auth, StreamWatcherListener(), timeout=None, secure=True)
	stream.userstream()

if __name__ == u'__main__':
	try:
		main()
	except KeyboardInterrupt:
		#savecfg()
		print u'Exiting...'




