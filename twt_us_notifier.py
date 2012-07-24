#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import hashlib
import urllib2
import re
import json
import os
import sys
import getopt
from BeautifulSoup import BeautifulStoneSoup

import tweepy
from getpass import getpass
from textwrap import TextWrapper
try:
	import glib
	import pynotify
	pynotify.init('twitter_notifier')
except:
	# non-linux compat
	# FIXME
	class glib:
		class GError:
			pass

g_twitter = None


def decodehtmlentities(data):
	return unicode(BeautifulStoneSoup(data, convertEntities=BeautifulStoneSoup.HTML_ENTITIES))

def notify_gnome(title, msg, icon=None):
	try:
		pynotify.Notification(title, msg, icon).show()
	except glib.GError:
		# glib.GError: Reached stack-limit of 50
		pass
	except:
		pass

def download(url, filename):
	data=urllib2.urlopen(url).read()
	open(filename, u'w').write(data)

def get_image(url):
	if g_twitter.config.get('get_original_img', False):
		url = re.sub('_normal(?=\.)', '', url)

	hashed = hashlib.sha1(url).hexdigest()
	filename = u'%s/cache/%s' % (os.getcwd(), hashed)
	try:
		open(filename).close()
	except IOError:
		print u'* Downloading %s as %s' % (url, filename)
		download(url, filename)
		open(u'./cache/list.txt', u'a').write(u'%s\t%s\n' % (hashed, url))
	
	return filename


class StreamWatcherListener(tweepy.StreamListener):
	status_wrapper = TextWrapper(width=60, initial_indent=u'    ', subsequent_indent=u'    ')
	
	def on_data(self, data):
		super(StreamWatcherListener, self).on_data(data)
		g_twitter.streamlogfile.write(data)
		g_twitter.streamlogfile.write(u'\n')
		g_twitter.streamlogfile.flush()

	def on_status(self, status):
		try:
			etcinfo = u'%s  %s  via %s' % (status.author.screen_name, status.created_at, status.source)
			etcinfo_term = u'\033[4m\033[1m\033[34m%s\033[0m\033[32m  %s  via %s\033[0m' % (status.author.screen_name, status.created_at, status.source)
			profile_image = get_image(status.author.profile_image_url)
		except AttributeError:
			# sometimes status update lacks `author' key
			return

		print u'tweet %s' % status.id
		print u'\033[1m' + self.status_wrapper.fill(status.text) + '\033[0m'
		print u'%s\n========================================\n' % etcinfo_term

		statustext = decodehtmlentities(status.text)

		notify_gnome(statustext, etcinfo, profile_image)

	def on_error(self, status_code):
		print u'An error has occured! Status code = %s' % status_code
		return True  # keep stream alive

	def on_timeout(self):
		print u'timeout'

class Twitter(object):
	def __init__(self):
		self.cfgfile= None
		self.config = {}
		self.streamlogfile = open(u'./tweets.txt', u'a')

	def _loadcfg(self, filename):
		try:
			self.config = json.load(open(filename))
		except (IOError, ValueError):
			key = raw_input(u'consumer_key: ')
			secret = raw_input(u'consumer_secret: ')
			self.config = {'consumer_key': key, 'consumer_secret': secret}
	def init(self, cfgfile):
		self.cfgfile = cfgfile
		self._loadcfg(cfgfile)
		self.authorize()
	def savecfg(self, filename):
		json.dump(self.config, open(filename, u'w'))

	def authorize(self):
		auth = tweepy.OAuthHandler(self.config[u'consumer_key'], self.config[u'consumer_secret'])
		if u'access_token_key' not in self.config:
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

				self.config[u'access_token_key'] = auth.access_token.key
				self.config[u'access_token_secret'] = auth.access_token.secret
				# FIXME
				self.savecfg(self.cfgfile)

				print(u'OK. Now restart the program.')

			return
		else:
			auth.set_access_token(self.config[u'access_token_key'], self.config[u'access_token_secret'])
			self.auth = auth
			self.api = tweepy.API(auth)

	def main_userstream(self, argv):
		opts, args = getopt.gnu_getopt(argv, u'h')
		for o, a in opts:
			if o == u'-h':
				print(u'%s: Start user stream notification service' % argv[0])
				print(u'Usage: %s' % argv[0])
				return
		stream = tweepy.Stream(self.auth, StreamWatcherListener(), timeout=None, secure=True)
		stream.userstream()

	def main_tweet(self, argv):
		opts, args = getopt.gnu_getopt(argv, u'hr:')
		reply_to = None
		for o, a in opts:
			if o == u'-h':
				print(u'%s: update status' % argv[0])
				print(u'Usage: %s [<status text>]' % argv[0])
				return
			elif o == u'-r':
				reply_to = a
		text = ' '.join(args[1:])
		if text == '':
			text = raw_input()
			if text == '':
				return False
		res = self.api.update_status(text, in_reply_to_status_id=reply_to)
		if not res:
			return False

	def main_main(self, argv):
		print(u'Usage: %s <program_name> [-h] args...' % argv[0])
		print(u'Programs:')
		print(u'\tuserstream')
		print(u'\ttweet')

def main():
	global g_twitter
	g_twitter = Twitter()

	programs = {
		u'userstream': g_twitter.main_userstream,
		u'tweet': g_twitter.main_tweet,
	}
	argv = sys.argv
	try:
		program = programs[argv[0]]
	except KeyError:
		if len(argv) >=2:
			try:
				program = programs[argv[1]]
				argv = argv[1:]
			except KeyError:
				program = g_twitter.main_main
		else:
			program = g_twitter.main_main

	g_twitter.init(u'./config.txt')
	ret = program(argv)
	if ret != False:
		sys.exit(0)
	else:
		sys.exit(1)

if __name__ == u'__main__':
	try:
		main()
	except KeyboardInterrupt:
		#savecfg()
		print u'Exiting...'




