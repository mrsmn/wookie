#!/usr/bin/env python
# -*- coding: utf-8 -*-

__appname__ = "wookie"
__version__ = "v.2.1"
__author__  = "@c0ding"
__date__    = "April 2014"
__license__ = "Apache v2.0 License"

import re
import os
import time
import irclib
import calendar
import threading
import feedparser
from datetime import datetime
from datetime import timedelta

wookie_start_time = time.time()

#CONFiG:
network = 'irc.example.net'
port = 6667
channels = ['#channel']
nick = 'wookie'
name = 'wookie v.2.1 is available at https://github.com/c0ding/wookie'
password = 'NickServ password'

announce_list = ["url_feed_1"]
request_list = ["url_feed_2"]
announce_entries_file = os.environ.get("HOME") + "/.b0t/announce-entries"
request_entries_file = os.environ.get("HOME") + "/.b0t/request-entries"

#COMMAND CAPABiLiTY AND DEBUG
def on_pubmsg(connection, event):
	if event.arguments() [0].lower() == '.help':
		connection.privmsg(channel, "\x02Available commands are\x02: .help || .version || .uptime || .restart || .quit")
	if event.arguments() [0].lower() == '.version':
		connection.privmsg(channel, "\x02Version\x02: wookie v.2.1 is available at https://github.com/c0ding/wookie")
	if event.arguments() [0].lower() == '.uptime':
		uptime_raw = round(time.time() - wookie_start_time)
		uptime = timedelta(seconds=uptime_raw)
		connection.privmsg(channel, "\x02Uptime\x02: up {}".format(uptime))
	if event.arguments() [0].lower() == ".restart":
		connection.quit()
		wookie_dir = os.environ.get("HOME") + "/path/to/wookie/dir"
		os.chdir(wookie_dir)
		os.system("nohup python wookie.py &")
	if event.arguments() [0].lower() == '.quit':
		connection.quit()
		
def on_invite(connection, event):
	connection.join(event.arguments() [0])
	
def on_kick(server, event):
	for channel in channels:
		server.join(channel)
		
def on_ctcp(connection, event):
	if event.arguments() [0].upper() == 'VERSION':
		connection.ctcp_reply(event.source().split('!') [0], 'wookie v.2.1 is available at https://github.com/c0ding/wookie')

def on_welcome(server, event):
    if password:
        server.privmsg("nickserv", "IDENTIFY %s" % password)
    server.privmsg("chanserv", "SET irc_auto_rejoin ON")
    server.privmsg("chanserv", "SET irc_join_delay 0")
    for channel in channels:
        server.join(channel)

irclib.DEBUG = 1
irc = irclib.IRC()
irc.add_global_handler ('pubmsg', on_pubmsg)
irc.add_global_handler ('invite', on_invite)
irc.add_global_handler ('welcome', on_welcome)
irc.add_global_handler ('kick', on_kick)
irc.add_global_handler ('ctcp', on_ctcp)

#CREATE SERVER OBJECT, CONNECT TO SERVER AND JOiN CHANNELS
server = irc.server()
server.connect(network, port, nick, ircname=name, ssl=False)

msgqueue = []

def announce_refresh():
    FILE = open(announce_entries_file, "r")
    filetext = FILE.read()
    FILE.close()
    for feed in announce_list:
        NextFeed = False
        d = feedparser.parse(feed)
        for entry in d.entries:
            id = entry.link.encode('utf-8')+entry.title.encode('utf-8')
            if id in filetext:
                NextFeed = True
            else:
                FILE = open(announce_entries_file, "a")
                FILE.write(id + "\n")
                FILE.close()
                title = entry.title.encode('utf-8')
                url = entry.link.encode('utf-8')
                category = title.split(' -', 1 )[0]
                title = title.split('- ', 1 )[1]
                title = title.replace(' ', '.')
                description = entry.description.encode('utf-8')
                result = re.search(r'Size : ([0-9]+\.?[0-9]*? [A-Za-z]{2})',description)
                size = result.group(1)
                entryDate = d.entries[0].published
                ReleaseDate = entryDate.split(' +', 1 )[0]
                gReleaseDate = re.search(r'Ajouté le : ([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})', description)
                gPreDate = re.search(r'PreTime : ([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})', description)
                if gPreDate is None:
                    pretime = ""
                else:
                    sPreDate = gPreDate.group(1)
                    sReleaseDate = gReleaseDate.group(1)
                    fmt = '%Y-%m-%d %H:%M:%S'
                    releaseDate = datetime.strptime(sReleaseDate, "%Y-%m-%d %H:%M:%S")
                    preDate = datetime.strptime(sPreDate, "%Y-%m-%d %H:%M:%S")
                    def timestamp(date):
                        return calendar.timegm(date.timetuple())
                    pre = (timestamp(releaseDate)-timestamp(preDate))
                    years, remainder = divmod(pre, 31556926)
                    days, remainder1 = divmod(remainder, 86400)
                    hours, remainder2 = divmod(remainder1, 3600)
                    minutes, seconds = divmod(remainder2, 60)

                    if pre < 60:
                        pretime = '%ssecs after Pre' % (seconds)
                    elif pre < 3600:
                        pretime = '%smin %ssecs after Pre' % (minutes, seconds)
                    elif pre < 86400:
                        pretime = '%sh %smin after Pre' % (hours, minutes)
                    elif pre < 172800:
                        pretime = '%sjour %sh after Pre' % (days, hours)
                    elif pre < 31556926:
                        pretime = '%sjours %sh after Pre' % (days, hours)
                    elif pre < 63113852:
                        pretime = '%san %sjours after Pre' % (years, days)
                    else:
                        pretime = '%sans %sjours after Pre' % (years, days)


                msgqueue.append("\033[37m" + "[" + "\033[31m" + category + "\033[37m" + "]" + " - " + "\033[35m" + url + title + " " + "\033[37m" + "[" + size + "] " + pretime)


def request_refresh():
    FILE = open(request_entries_file, "r")
    filetext = FILE.read()
    FILE.close()
    for feed in request_list:
        NextFeed = False
        d = feedparser.parse(feed)
        for entry in d.entries:
            id = entry.link.encode('utf-8')+entry.title.encode('utf-8')
            if id in filetext:
                NextFeed = True
            else:
                FILE = open(request_entries_file, "a")
                FILE.write(id + "\n")
                FILE.close()
                title = entry.title.encode('utf-8')
                url = entry.link.encode('utf-8')
                title = title.split(' - ', 1 )[0]

                msgqueue.append("\x02" + "Requests : " + "\x02" + title + " " + url)

            if NextFeed:
                break;

    threading.Timer(5.0, announce_refresh).start()
    threading.Timer(5.0, request_refresh).start()

announce_refresh()
request_refresh()

def main():
	while 1:
	    while len(msgqueue) > 0:
	        msg = msgqueue.pop()
	        for channel in channels:
	            server.privmsg(channel, msg)
	    time.sleep(1)
	    irc.process_once()
	    time.sleep(1)

if __name__ == "__main__":
	main()
