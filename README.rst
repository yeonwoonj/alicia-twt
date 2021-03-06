﻿=====================================================
alicia-twt : post a tweet for each `alicia freeboard <http://alicia.gametree.co.kr/Community/List.aspx?BoardType=1>`_'s article at gametree.
=====================================================

License:
======
 Public domain


Changes:
=======
- 2011-06-13. fix bug that /m/cont doesn't handle image file extension except jpg.
- 2011-05-03. add message for homepage maintenance.
- 2011-04-24. fix extract GM nickname properly also.
- 2011-04-12. add keyword monitoring reports to yammer feature.
- 2011-04-11. add db dump, add keyword monitoring feature.
- 2011-03-21. fix urlfetch cache problem.
- 2011-03-21. let each /m/cont page has its own title.
- 2011-02-23. add twitter message manipulation to avoid search: 앨리샤 -> 앨ㄹ1샤
- 2011-02-21. add mobile page for detail view (alpha)
- 2011-02-19. fix improper parsing error when title contains double-quotation-mark.
- 2011-02-19. fix item has been processed reversed order in a page.
- 2011-02-19. add to github repo
- 2011-02-17. inital version


How to run this program:
==================
 1. this program runs under the Google App Engine environment.
 2. first, install Google App Engine SDK. (download: http://code.google.com/appengine/downloads.html)
 3. rename alicia-twt-public.py to alicia-twt.py.
 4. edit alicia-twt.py : replace twitter api key and j.mp url shortener api key with your own one.
 5. download oauth.py (https://github.com/mikeknapp/AppEngine-OAuth-Library)
 6. done! run the program locally(dev_appserver.py) if you need some tests, or deploy to appspot.com(appcfg.py) for the live service.
