#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import string
import datetime
import time

import logging
import oauth
import urllib

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.ext import db
from google.appengine.api import urlfetch

from google.appengine.ext.webapp import template

from django.utils import simplejson

# ------------------------------------------------------------------------------
# DB Model

class BoardItem(db.Model):
    title = db.StringProperty()
    text  = db.StringProperty(multiline=True)
    pubDate = db.StringProperty()
    no    = db.IntegerProperty()
    link  = db.StringProperty()
    tweet = db.BooleanProperty()
    author = db.StringProperty()
    #cont_long = db.StringProperty(multiline=True)
    #comments  = db.StringListProperty()


# ------------------------------------------------------------------------------
# global utility function

class Helper:
    def isRelease(self, host):
        return host != "localhost:8080"

    def isDebug(self, host):
        return not self.isRelease(host)

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
                                                                                                  'url':urllib.quote(s)}
        #logging.info(url)
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
# crawl handler

class CrawlHandler(webapp.RequestHandler):
    site = 'http://alicia.gametree.co.kr'
    site_mobile = 'http://alicia-twt.appspot.com/m/cont/'
    
    def get(self, mode=''):

        if mode == 'pages':
            self.processPages()            
        elif re.search('cont/\d+', mode):
            match = re.search('.*/(\d+)', mode)
            if match:
                no = match.group(1)
                self.processCont(no)
            else:
                self.response.out.write("")

    def processPage(self, url):
        """
        process a page, return False if already processed article had been found or an error occured.
        """

        try:
            res = urlfetch.fetch(url)
        except Exception:
            time.sleep(5)
            return self.processPage(url)
            
        if res.status_code != 200:
            logging.error('processPage - urlfetch error: status_code(%d)' % res.status_code)
            return False

        wholeNew = True # 전체가 새로운 게시글인가?
        s = res.content.decode('utf-8')
        
        #self.response.out.write('<ul>')
        re_findlist = re.compile('<td class="left top_line">(.*?)</td>', re.DOTALL)
        items = re_findlist.findall(s)

        logging.info('processItem - found items: items(%s),contents(%s)' % (len(items), len(s)))

        for item in items[::-1]:
            re_text = re.compile('title="(.*?)">', re.DOTALL)
            text = re_text.findall(item)
            name = re.findall('<span class="name">(.*?)</span>', item)
            date = re.findall('<span class="date">(.*?)</span>', item)
            link = re.findall('href="(.*?)"', item)

            if self.processItem(name[0], text[0], text[1], date[0], self.site + link[0]) == False:
                wholeNew = False
        #self.response.out.write('</ul>')

        return wholeNew

    def processItem(self, name, title, cont, date, link):
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
        item.author  = name
        item.title   = title
        item.text    = cont
        item.pubDate = date
        item.no      = int(no)

        host = self.request.headers["Host"]
        if helper.isRelease(host):
            link = self.site_mobile + no
            shorten_link = jmp().shorten(link)

            message = self.format_message(title,cont,date,shorten_link)

            item.link  = shorten_link
            if len(message) < 77:
                # 너무 짧은 글은 트윗하지 않는다.
                item.tweet = True
            else:
                # 앨리샤 -> 앨ㄹ1샤로 변환 (검색에 걸리지 않게하려고)
                message = re.sub(u'(앨리샤|엘리샤)', u'앨ㄹ1샤', message)
                item.tweet = twt().status(message)

        else:
            message = self.format_message(title,cont,date,link)
            self.response.out.write("[%s]%s<br />\n" % (tweet,message))
            
            item.link = link
            item.tweet = True

        item.put()

        return True

    def format_message(self, title, cont, date, shorten_link):
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

        return message

    def processPages(self):
        """
        crawl pages
        """
        d = datetime.datetime.now()
        url_prefix = 'http://alicia.gametree.co.kr/Community/List.aspx?BoardType=1&PageNo='

        pageLimit = 10
        host = self.request.headers["Host"]
        if helper.isDebug(host):
            pageLimit = 3

        for pageNo in range(1,pageLimit):
            #logging.info('process page %d' % pageNo)
            if self.processPage("%s%s&%s" % (url_prefix,str(pageNo),d.strftime("%Y%m%d%H%M"))) == False:
                break

            if pageNo == (pageLimit - 1):
                logging.error('too many unread items - stop fetching at: pageNo(%d)' % pageNo)
                break

    def processCont(self, no):
        """
        crawl entire content and comments
        """
        url_prefix = 'http://alicia.gametree.co.kr/Community/View.aspx?BoardType=1&PageNo=1&BoardNo='
        url = url_prefix + no
        try:
            res = urlfetch.fetch(url)
        except Exception:
            time.sleep(5)
            return self.processCont(no)
            
        if res.status_code != 200:
            logging.error('processCont - urlfetch error: status_code(%d)' % res.status_code)
            return False

        s = res.content.decode('utf-8')

        if len(s) < 200:
            json = u'{"result":"삭제된 게시물입니다."}'
            return self.response.out.write(json)

        # parse content
        name = re.search('<span class="name">(.*?)</span>', s)
        name = name.group(1)

        head = s.find('<div class="n-view">')
        tail = s.find('<div class="n-reply-up" id="n-reply-up">')
        body = s[head:tail]

        images = re.findall('"/_Files/CommunityAttach/FreeBoard/(.*?).jpg"', body)
        imgtag = '<div id="n-gallery">'
        for img in images:
            imgtag += u'<img src="http://alicia.gametree.co.kr/_Files/CommunityAttach/FreeBoard/%s.jpg" alt="첨부파일" /><br />' % img
        imgtag += '</div>'
        imgtag = re.sub('[\r\n]','', imgtag.strip())
        imgtag = re.sub('"', '\\"', imgtag)
            
        re_cont = re.compile('<div class="nv-desc noline">(.*?)</div>', re.DOTALL)
        cont = re_cont.search(body).group(1)
        cont = re.sub('[\r\n]','', cont.strip())
        cont = re.sub('"', '\\"', cont)

        cont_all = imgtag + cont

        re_comment = re.compile('<p class="r-info"><strong>(.*?)</strong>.*?</p>.*?<p class="r-desc">(.*?)</p>', re.DOTALL)
        comments = re_comment.findall(s)

        # parse comments
        arr = []
        for c in comments:
            name = c[0]
            re_name = re.search('alt="(.*?)"', name)
            if re_name:
                name = re_name.group(1)

            cont = re.sub('[\r\n]','', c[1])
            cont = re.sub('"', '\\"', cont)

            arr.append(simplejson.dumps({'name':name,'cont':cont}))

        # make JSON string

        result = len(comments)
        if result > 0:
            result = u'댓글 %d개' % result
        else:
            result = u'댓글이 없습니다.'

        json = u'{"result": "%(result)s", "name": "%(name)s", "cont": "%(cont)s", "comments": [%(comments)s]}' % {'result': result,
                                                                                                                  'name': name,
                                                                                                                  'cont': cont_all,
                                                                                                                  'comments': ','.join(arr)}

        self.response.out.write(json)


# ------------------------------------------------------------------------------
# mobile handler

class MobileHandler(webapp.RequestHandler):
    
    def get(self, mode=''):

        if mode == 'list':
            gql = BoardItem.all().order('-pubDate')
            items = gql.fetch(100)
            #self.response.out.write(len(items))

            template_values = {
                'items' : items
                }

            path = os.path.join(os.path.dirname(__file__), 'list.html')
            self.response.out.write(template.render(path, template_values))

        if re.search('cont/\d+', mode):
            match = re.search('.*/(\d+)', mode)
            if match:
                no = match.group(1)
                items = BoardItem.gql("WHERE no = :no", no=int(no))
                if items.count():
                    url_prefix = 'http://alicia.gametree.co.kr/Community/View.aspx?BoardType=1&PageNo=1&BoardNo='
                    template_values = {
                        'item' : items[0],
                        'cont' : re.sub('[\r\n]','<br />',items[0].text),
                        'link' : url_prefix + str(items[0].no)
                        }

                    path = os.path.join(os.path.dirname(__file__), 'cont.html')
                    self.response.out.write(template.render(path, template_values))


# ------------------------------------------------------------------------------
# twitter client handler

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


# ------------------------------------------------------------------------------
# test handler

class TestHandler(webapp.RequestHandler):
    def get(self):
        host = self.request.headers["Host"]
        if helper.isRelease(host):
            #url_prefix = 'http://alicia.gametree.co.kr/Community/List.aspx?BoardType=1&PageNo='
            #self.downloadPage('%s1&%s' % (url_prefix, d.strftime("%Y%m%d%H%M")))
            return
        
        self.response.out.write(host)

    def downloadPage(self, url):
        try:
            res = urlfetch.fetch(url)
        except Exception:
            time.sleep(5)
            return self.downloadPage(url)

        if res.status_code != 200:
            logging.error('processPage - urlfetch error: status_code(%d)' % res.status_code)
            return False

        s = res.content.decode('utf-8')
        self.response.out.write(s)

        #re_findlist = re.compile('<td class="left top_line">(.*?)</td>', re.DOTALL)
        #items = re_findlist.findall(s)

        #logging.info('processItem - found items: items(%s),contents(%s)' % (len(items), len(s)))

# ------------------------------------------------------------------------------

def main():
    application = webapp.WSGIApplication([('/crawl/(.*)', CrawlHandler),
                                          ('/m/(.*)', MobileHandler),
                                          ('/twt/(.*)', TwitterClientHandler),
                                          ('/test', TestHandler),
                                          ('/', MainHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
