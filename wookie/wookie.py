#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ssl
import time
import irclib
import calendar
import threading
import feedparser
from irclib import SimpleIRCClient
from threading import (Thread, Event)
from datetime import (datetime, timedelta)
from config import (feeds, wookie, network)
from django.utils.encoding import smart_str

__appname__ = "wookie"
__version__ = "v.3.0"
__author__ = "@c0ding, @grm34"
__date__ = "2012 - 2014"
__license__ = "Apache v2.0 License"

announce_entries_file = os.environ.get("HOME") + "/.wookie/announce-entries"
request_entries_file = os.environ.get("HOME") + "/.wookie/request-entries"


class Queue_Manager(Thread):

    def __init__(self, connection, delay=feeds['delay']):
        Thread.__init__(self)
        self.setDaemon(1)
        self.connection = connection
        self.delay = delay
        self.event = Event()
        self.queue = []

    def run(self):
        while 1:
            self.event.wait()
            while self.queue:
                (msg, target) = self.queue.pop(0)
                self.connection.privmsg(target, msg)
                time.sleep(self.delay)
            self.event.clear()

    def send(self, msg, target):
        self.queue.append((msg.strip(), target))
        self.event.set()


class _wookie(SimpleIRCClient):

    def __init__(self):
        irclib.SimpleIRCClient.__init__(self)
        self.start_time = time.time()
        self.owner = wookie['bot_owner']
        self.channel = network['channels']
        self.queue = Queue_Manager(self.connection)

    def on_welcome(self, serv, ev):
        if network['password']:
            serv.privmsg(
                "nickserv",
                "IDENTIFY {}".format(network['password']))
            serv.privmsg("chanserv", "SET irc_auto_rejoin ON")
            serv.privmsg("chanserv", "SET irc_join_delay 0")
        for channel in self.channel:
            serv.join(channel)

        self.queue.start()
        self.announce_refresh()
        self.request_refresh()

    def on_rss_entry(self, text):
        for channel in self.channel:
            self.queue.send(text, channel)

    def on_kick(self, serv, ev):
        serv.join(ev.target())

    def on_invite(self, serv, ev):
        serv.join(ev.arguments()[0])

    def on_ctcp(self, serv, ev):
        if ev.arguments()[0].upper() == 'VERSION':
            serv.ctcp_reply(
                ev.source().split('!')[0], network['bot_name'])

    def on_pubmsg(self, serv, ev):
        author = irclib.nm_to_n(ev.source())
        event_time = time.strftime('[%H:%M:%S]', time.localtime())
        print ('{} {}: {}'.format(event_time, author, ev.arguments()[0]))
        chan = ev.target()

        # Owner options
        try:
            if (author == self.owner):
                if ev.arguments()[0].lower() == ".restart":
                    serv.disconnect()
                    os.chdir(wookie['path'])
                    os.system('nohup python wookie.py &')
                if ev.arguments()[0].lower() == '.quit':
                    serv.disconnect()
                    sys.exit(1)
        except OSError as error:
            print (
                '{}\nYou should specify the wookie path in'
                ' config.py !'.format(error))

        # Public Options
        if ev.arguments()[0].lower() == '.help':
            serv.privmsg(
                chan, '\x02Available commands are\x02: .help || '
                      '.version || .uptime || .restart || .quit')
        if ev.arguments()[0].lower() == '.version':
            serv.privmsg(chan, network['bot_name'])
        if ev.arguments()[0].lower() == '.uptime':
            uptime_raw = round(time.time() - self.start_time)
            uptime = timedelta(seconds=uptime_raw)
            serv.privmsg(chan, '\x02Uptime\x02: {}'.format(uptime))

    def announce_refresh(self):
        try:
            FILE = open(announce_entries_file, "r")
            filetext = FILE.read()
            FILE.close()

            for feed in feeds['announce']:
                d = feedparser.parse(feed)
            for entry in d.entries:
                id_announce = '{0}{1}'.format(smart_str(entry.link),
                                              smart_str(entry.title))
                if id_announce not in filetext:
                    url = smart_str(entry.link)
                    title = smart_str(
                        entry.title).split('- ', 1)[1].replace(' ', '.')
                    size = smart_str(
                        entry.description).split('|')[1]\
                                          .replace('Size :', '')\
                                          .strip()
                    category = smart_str(entry.title).split(' -', 1)[0]
                    if len(entry.description.split('|')) == 5:
                        pretime = ''
                    else:
                        releaseDate = datetime.strptime(smart_str(
                            entry.description).split('|')[2]
                                              .replace('Ajouté le :', '')
                                              .strip(),
                            '%Y-%m-%d %H:%M:%S')
                        preDate = datetime.strptime(smart_str(
                            entry.description).split('|')[5]
                                              .replace('PreTime :', '')
                                              .strip(),
                            '%Y-%m-%d %H:%M:%S')

                        def timestamp(date):
                            return calendar.timegm(date.timetuple())

                        pre = (timestamp(releaseDate)-timestamp(preDate))
                        years, remainder = divmod(pre, 31556926)
                        days, remainder1 = divmod(remainder, 86400)
                        hours, remainder2 = divmod(remainder1, 3600)
                        minutes, seconds = divmod(remainder2, 60)

                        if pre < 60:
                            pretime = '{}secs after Pre'\
                                .format(seconds)
                        elif pre < 3600:
                            pretime = '{0}min {1}secs after Pre'\
                                .format(minutes, seconds)
                        elif pre < 86400:
                            pretime = '{0}h {1}min after Pre'\
                                .format(hours, minutes)
                        elif pre < 172800:
                            pretime = '{0}jour {1}h after Pre'\
                                .format(days, hours)
                        elif pre < 31556926:
                            pretime = '{0}jours {1}h after Pre'\
                                .format(days, hours)
                        elif pre < 63113852:
                            pretime = '{0}an {1}jours after Pre'\
                                .format(years, days)
                        else:
                            pretime = '{0}ans {1}jours after Pre'\
                                .format(years, days)

                    self.on_rss_entry(
                        '\033[37m[\033[31m{0}\033[37m] - \033[35m'
                        '{1}{2} \033[37m[{3}] {4}'.format(
                            category, url, title, size, pretime))
                    FILE = open(announce_entries_file, "a")
                    FILE.write("{}\n".format(id_announce))
                    FILE.close()

            threading.Timer(5.0, self.announce_refresh).start()

        except IOError as error:
            print (
                '{}\nYou should create a file named announce-entries'
                ' in the .wookie folder of your home directory!'
                .format(error))

    def request_refresh(self):
        try:
            FILE = open(request_entries_file, "r")
            filetext = FILE.read()
            FILE.close()

            for feed in feeds['request']:
                d = feedparser.parse(feed)
            for entry in d.entries:
                id_request = '{0}{1}'.format(
                    smart_str(entry.link),
                    smart_str(entry.title).split(' - ')[0])
                if id_request not in filetext:
                    title = smart_str(entry.title).split(' - ', 1)[0]
                    url = smart_str(entry.link)
                    self.on_rss_entry(
                        '\x02Requests : \x02{0} {1}'.format(title, url))
                    FILE = open(request_entries_file, "a")
                    FILE.write('{}\n'.format(id_request))
                    FILE.close()

            threading.Timer(5.0, self.request_refresh).start()

        except IOError:
            print (
                '{}\nYou should create a file named request-entries'
                ' in the .wookie folder of your home directory!'
                .format(error))


def main():
    bot = _wookie()
    try:
        bot.connect(
            network['server'], network['port'], network['bot_nick'],
            network['bot_name'], ssl=network['SSL'], ipv6=network['ipv6'])
    except irclib.ServerConnectionError as error:
        print (error)
        sys.exit(1)
    bot.start()

if __name__ == "__main__":
    main()
