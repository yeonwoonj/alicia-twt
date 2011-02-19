#!/usr/bin/env python
# -*- coding: cp949 -*-

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.ext import db
from google.appengine.api import urlfetch

from django.utils import simplejson

import re
import string
import datetime
import time

import logging
import oauth
import urllib

# ------------------------------------------------------------------------------
# DB Model

class BoardItem(db.Model):
    title = db.StringProperty()
    text  = db.StringProperty(multiline=True)
    pubDate = db.StringProperty()
    no    = db.IntegerProperty()
    link  = db.StringProperty()
    tweet = db.BooleanProperty()


# ------------------------------------------------------------------------------
# global utility function

class Helper:
    def isRelease(self, host):
        return host != "localhost:8080"

helper = Helper()

# ------------------------------------------------------------------------------
# twitter api

class twt:
    appkey = ''
    appsec = ''
    user_token = ''
    user_secret = ''

    def status(self, s):
        status_url = 'http://api.twitter.com/1/statuses/update.xml'
        client = oauth.TwitterClient(self.appkey, self.appsec, '')
        result = client.make_request(url=status_url, token=self.user_token, secret=self.user_secret, additional_params={'status':s}, method=urlfetch.POST)
        wasOK = result.status_code == 200
        if wasOK:
            """
            logging.info(result.content)
            """
        else:
            logging.error(s)
            logging.error(result.content)
        return wasOK


# ------------------------------------------------------------------------------
# jmp shortener api

class jmp:
    apikey = ''
    loginid = ''

    def shorten(self, s):
        if re.search('http://(bit\.ly|j\.mp)', s):
            logging.info('%s is a already shorten!' % s)
            return s

        url = 'http://api.j.mp/v3/shorten?login=%(loginid)s&apiKey=%(apikey)s&longUrl=%(url)s' % {'loginid':self.loginid,
                                                                                                  'apikey':self.apikey,
                                                                                                  'url':urllib.quote(s) }
        logging.info(url)
        res = urlfetch.fetch(url);
        if res.status_code == 200:
            json = simplejson.loads(res.content)
            if int(json['status_code']) == 200:
                return json['data']['url']
            else:
                logging.error(res.content)
        else:
            logging.error(res.content)
            
        return s

# ------------------------------------------------------------------------------
# default handler

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<a href="http://twitter.com/alicia_twt">http://twitter.com/alicia_twt</a>')

# ------------------------------------------------------------------------------
# alicia handler

class AliciaHandler(webapp.RequestHandler):
    site = 'http://alicia.gametree.co.kr'
    
    def get(self):
        url_prefix = 'http://alicia.gametree.co.kr/Community/List.aspx?BoardType=1&PageNo='

        for pageNo in range(1,10):
            logging.info('process page %d' % pageNo)
            if self.process(url_prefix + str(pageNo)) == False:
                break

            if pageNo == 9:
                logging.error('too many unread items - stop fetching at: pageNo(%d)' % pageNo)
                break

    def process(self, url):
        """
        process a page, return False if already processed article had been found or an error occured.
        """

        try:
            res = urlfetch.fetch(url)
        except Exception:
            time.sleep(5)
            return self.process(url)
            
        if res.status_code != 200:
            logging.error('urlfetch error: status_code(%d)' % res.status_code)
            return False

        wholeNew = True # 전체가 새로운 게시글인가?
        s = res.content.decode('utf-8')
        
        #self.response.out.write('<ul>')
        re_findlist = re.compile('<td class="left top_line">(.*?)</td>', re.DOTALL)
        items = re_findlist.findall(s)
        for item in items:
            re_text = re.compile('title="(.*?)"', re.DOTALL)
            text = re_text.findall(item)
            date = re.findall('<span class="date">(.*?)</span>', item)
            link = re.findall('href="(.*?)"', item)

            if self.processItem(text[0], text[1], date[0], self.site + link[0]) == False:
                wholeNew = False
        #self.response.out.write('</ul>')

        return wholeNew

    def processItem(self, title, cont, date, link):
        """
        return False if already processed.
        """

        no = re.findall('BoardNo=(\d+)', link)[0]
        
        tweet = False
        savedItem = BoardItem.gql("WHERE no = :no", no=int(no))
        if savedItem.count():
            tweet = savedItem[0].tweet
            if tweet:
                # already processed
                return False

        item = BoardItem(key_name=no)
        item.title = title
        item.text  = cont
        item.pubDate = date
        item.no    = int(no)

        host = self.request.headers["Host"]
        if helper.isRelease(host):
            shorten_link = jmp().shorten(link)

            shorten_title = title[:30]
            if shorten_title != title:
                shorten_title = shorten_title.strip() + u"…"

            shorten_cont = cont[:80]
            if shorten_cont != cont:
                shorten_cont = shorten_cont.strip() + u"…"

            message = u'「%(title)s」 %(cont)s %(link)s' % {'title': shorten_title.strip(),
                                                           'cont': shorten_cont.strip(),
                                                           'date': date,
                                                           'link' : shorten_link}
            #self.response.out.write("[%s]%s<br />\n" % (tweet,message))

            item.link  = shorten_link
            if len(shorten_title+shorten_cont) < 40:
                # 너무 짧은 글은 트윗하지 않는다.
                item.tweet = True
            else:
                item.tweet = twt().status(message)

        else:
            item.link = ""
            item.tweet = True

        item.put()

        return True


class TwitterClientHandler(webapp.RequestHandler):
    def get(self, mode=''):
        host = self.request.headers["Host"]
        if helper.isRelease(host):
            return

        sss = u'123!abc~'

        # twitter - post a message

        user_token = twt().user_token
        user_secret = twt().user_secret

        appkey = twt().appkey
        appsec = twt().appsec
        callback_url = "%s/twt/verify" % self.request.host_url
        client = oauth.TwitterClient(appkey, appsec, callback_url)

        if mode == 'login':
            return self.redirect(client.get_authorization_url())
            
        if mode == 'verify':
            auth_token = self.request.get("oauth_token")
            auth_verifier = self.request.get("oauth_verifier")
            user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)
            return self.response.out.write(user_info)

        if mode == 'timeline':
            timeline_url = 'http://twitter.com/statuses/user_timeline.xml'
            result = client.make_request(url=timeline_url, token=user_token, secret=user_secret)
            return self.response.out.write(result.content)

        if mode == 'status':
            status_url = 'http://api.twitter.com/1/statuses/update.json'
            result = client.make_request(url=status_url, token=user_token, secret=user_secret, additional_params={'status':sss}, method=urlfetch.POST)
            logging.info(result.content)
            return self.response.out.write(result.content)


        self.response.out.write("<a href='/twt/login'>Login via Twitter</a>")


class TestHandler(webapp.RequestHandler):
    def get(self):
        host = self.request.headers["Host"]
        if helper.isRelease(host):
            return
        
        self.response.out.write(host)


# ------------------------------------------------------------------------------

def main():
    application = webapp.WSGIApplication([('/alicia', AliciaHandler),
                                          ('/twt/(.*)', TwitterClientHandler),
                                          ('/test', TestHandler),
                                          ('/', MainHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
