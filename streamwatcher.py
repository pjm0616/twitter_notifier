#!/usr/bin/env python

import time

import hashlib
import urllib2
import json
import os

from getpass import getpass
from textwrap import TextWrapper
import pynotify
import tweepy


g_config_filename = './config.txt'
g_config = None

def notify_gnome(title, msg, icon=None):
	pynotify.Notification(title, msg, icon).show()

def download(url, filename):
	data=urllib2.urlopen(url).read()
	open(filename, 'w').write(data)

def get_image(url):
	hashed = hashlib.sha1(url).hexdigest()
	filename = '%s/cache/%s' % (os.getcwd(), hashed)
	try:
		open(filename).close()
	except IOError:
		print '* Downloading %s as %s' % (url, filename)
		download(url, filename)
		open('./cache/list.txt', 'a').write('%s\t%s\n' % (hashed, url))
	
	return filename

tweetlogfile = open('./tweets.txt', 'a')

class StreamWatcherListener(tweepy.StreamListener):

	status_wrapper = TextWrapper(width=60, initial_indent='    ', subsequent_indent='    ')
	
	def on_data(self, data):
		super(StreamWatcherListener, self).on_data(data)
		tweetlogfile.write(data)
		tweetlogfile.write('\n')
		tweetlogfile.flush()

	def on_status(self, status):
		try:
			etcinfo = '%s  %s  via %s' % (status.author.screen_name, status.created_at, status.source)
			profile_image = get_image(status.author.profile_image_url)
		except AttributeError:
			# sometimes status update lacks `author' key
			return
		
		print self.status_wrapper.fill(status.text)
		print '\n %s\n' % etcinfo

		notify_gnome(status.text, etcinfo, profile_image)

	def on_error(self, status_code):
		print 'An error has occured! Status code = %s' % status_code
		return True  # keep stream alive

	def on_timeout(self):
		print 'timeout'

def loadcfg():
	global g_config
	g_config = json.load(open(g_config_filename))
	g_config = dict(map(lambda x: (str(x[0]), str(x[1])), g_config.iteritems()))
def savecfg():
	global g_config
	json.dump(g_config, open(g_config_filename, 'w'))

def main():
	global g_config
	loadcfg()
	
	auth = tweepy.OAuthHandler(g_config['consumer_key'], g_config['consumer_secret'])
	if 'access_token_key' not in g_config:
		try:
			redirect_url = auth.get_authorization_url()
		except tweepy.TweepError as e:
			print 'Error! Failed to get request token.'
			print(e)
		else:
			print('Authorization URL: %s' % redirect_url)
			pincode = raw_input('enter PIN code: ')
			auth.get_access_token(pincode)
			print('Key: %s' % auth.access_token.key)
			print('Secret: %s' % auth.access_token.secret)
			
			g_config['access_token_key'] = auth.access_token.key
			g_config['access_token_secret'] = auth.access_token.secret
			savecfg()

			print('OK. Restart the program.')
		
		return
	else:
		auth.set_access_token(g_config['access_token_key'], g_config['access_token_secret'])
	
	stream = tweepy.Stream(auth, StreamWatcherListener(), timeout=None, secure=True)
	stream.userstream()

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		#savecfg()
		print 'Exiting...'




