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
import glib
import pynotify
import tweepy

pynotify.init('twitter_notifier')

g_config_filename = u'./config.txt'
g_config = None

def decodehtmlentities(data):
	return unicode(BeautifulStoneSoup(data, convertEntities=BeautifulStoneSoup.HTML_ENTITIES))

def notify_gnome(title, msg, icon=None):
	try:
		pynotify.Notification(title, msg, icon).show()
	except glib.GError:
		# glib.GError: Reached stack-limit of 50
		pass

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
			etcinfo_term = u'\033[4m\033[1m\033[34m%s\033[0m\033[32m  %s  via %s\033[0m' % (status.author.screen_name, status.created_at, status.source)
			profile_image = get_image(status.author.profile_image_url)
		except AttributeError:
			# sometimes status update lacks `author' key
			return
		
		print '\033[1m' + self.status_wrapper.fill(status.text) + '\033[0m'
		print u'%s\n========================================\n' % etcinfo_term
		
		statustext = decodehtmlentities(status.text)
		
		notify_gnome(statustext, etcinfo, profile_image)

	def on_error(self, status_code):
		print u'An error has occured! Status code = %s' % status_code
		return True  # keep stream alive

	def on_timeout(self):
		print u'timeout'

def loadcfg():
	global g_config
	try:
		g_config = json.load(open(g_config_filename))
	except (IOError, ValueError):
		key = raw_input(u'consumer_key: ')
		secret = raw_input(u'consumer_secret: ')
		g_config = {'consumer_key': key, 'consumer_secret': secret}
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




