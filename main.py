#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2015'

import webapp2
import jinja2
import os
from apiclient.discovery import build
from google.appengine.ext import webapp
from oauth2client.appengine import OAuth2Decorator, OAuth2DecoratorFromClientSecrets
from google.appengine.api import users
import httplib2
from google.appengine.ext import ndb
from oauth2client.appengine import CredentialsNDBProperty
from oauth2client.appengine import StorageByKeyName
from oauth2client.client import OAuth2WebServerFlow
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import memcache
import pickle
import json
from youtube import playlists, channels, playlist_sync, playlist_serch_or_create
from google.appengine.api import taskqueue
import time
import urlparse
import logging
from webapp2_extras import sessions
try:
    from settings import CLIENT_ID, CLIENT_SECRET
    from settings import SESSION_SECRET
except ImportError, e:
    raise ImportError('Error import settings module. Follow instructions on settings.py.template')



JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)+'/templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

JQUERY_URL = 'http://code.jquery.com/jquery-1.9.1.js'
JQUERY_UI_URL = 'http://code.jquery.com/ui/1.11.3/jquery-ui.min.js'
JQUERY_UI_CSS = 'http://code.jquery.com/ui/1.11.3/themes/smoothness/jquery-ui.css'

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': SESSION_SECRET,
}

class Credentials(ndb.Model):
  credentials = CredentialsNDBProperty()

class Tasks(ndb.Model):
    user_id = ndb.StringProperty()
    source_playlist_id = ndb.StringProperty()
    dest_playlist_id = ndb.StringProperty(required=False)
    playlist_title_prefix = ndb.StringProperty(required=False)
    updated = ndb.DateTimeProperty(auto_now=True)
    status = ndb.StringProperty(required=False)

def convertTasks(tasks):
    rv = map(lambda t: dict(t.to_dict(), **dict(id=t.key.id())), tasks)
    for t in rv:
        if t.get('updated'):
            t['updated'] = time.mktime(t['updated'].timetuple())
    return rv

class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
 
    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()

    def getYoutube(self, user_id, credentials):
        service = None

        http = httplib2.Http()
        http = credentials.authorize(http)
        service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, http=http)
        if user_id is None:
            self_channels = channels(service, part='id')
            if len(self_channels):
                user_id = self_channels[0].get('id')
                self.session['user_id'] = user_id
        return service

    def saveCredentials(self, user_id, credentials):
        if credentials.refresh_token:
            StorageByKeyName(Credentials, user_id, 'credentials').put(credentials)

# Sync requests
class SyncPlaylistHandler(BaseHandler):
    def post(self): # should run at most 1/s due to entity group limit
        task_id = self.request.get('task_id')
        logging.info('Task_id: %s', task_id) 
        t = Tasks.get_by_id(task_id)
        if t and (t.status is None or len(t.status)==0):
            credentials = StorageByKeyName(Credentials, t.user_id, 'credentials').get()
            if credentials:
                service = self.getYoutube(t.user_id, credentials)
                if t.dest_playlist_id is None:
                    source_playlist_info = playlists(service, playlist_id=t.source_playlist_id)
                    if len(source_playlist_info) == 0:
                        t.status = 'Sync error: can\'t found source playlist'
                        t.put()
                        return
                    source_playlist_info = source_playlist_info[0]
                    if t.playlist_title_prefix is None or len(t.playlist_title_prefix)==0:
                        title = source_playlist_info.get('snippet', {}).get('title')
                    else:
                        title = t.playlist_title_prefix + source_playlist_info.get('snippet', {}).get('title')
                    dest_playlist_info = playlist_serch_or_create(service, title)
                    if dest_playlist_info is None:
                        t.status = 'Sync error: can\'t create destination playlist'
                        t.put()
                        return
                    t.dest_playlist_id = dest_playlist_info.get('id')
                    t.put()
                code = playlist_sync(service, t.source_playlist_id, dest_playlist_id=t.dest_playlist_id)
                if code != 0:
                    t.status = 'Sync error: %d'%code
                self.saveCredentials(t.user_id, credentials)
            else:
                t.status = 'No access'
            t.put()

class SyncPlaylistCronHandler(BaseHandler):
    def get(self):
        for t in Tasks.query():
            taskqueue.add(url='/tasks/sync', params={'task_id': t.key.id() })

# Auth requests
class OAuthHandler(BaseHandler):
  def get(self):
    tmp_user_id = self.session.get('tmp_user_id')
    if tmp_user_id:
        flow = pickle.loads(memcache.get(tmp_user_id))
        if flow:
            credentials = flow.step2_exchange(self.request.params)
            service = self.getYoutube(None, credentials)
            StorageByKeyName(Credentials, self.session.get('user_id'), 'credentials').put(credentials)
        self.session.pop('tmp_user_id', None)
    self.redirect("/")

class YoutubeRedirectHandler(BaseHandler):
    def get(self, method):
        if method == 'auth':
            tmp_user_id = str(memcache.incr("auth_counter", initial_value=0))
            self.session['tmp_user_id'] = tmp_user_id
            flow = OAuth2WebServerFlow(
                # Visit https://code.google.com/apis/console to
                # generate your client_id, client_secret and to
                # register your redirect_uri.
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scope=YOUTUBE_READ_WRITE_SCOPE)
            callback = self.request.relative_url('/oauth2callback')
            authorize_url = flow.step1_get_authorize_url(callback)
            memcache.set(tmp_user_id, pickle.dumps(flow), time=600)
            self.redirect(authorize_url)
        elif method == 'logout':
            if self.session.get('user_id'):
                self.session.pop('user_id', None)
            self.redirect('/')

# Other 
class PlaylistsHandler(BaseHandler):
  def get(self, out_format):
    is_html = out_format.lower() == 'html'
    user_id = self.session.get('user_id')
    if user_id:
        credentials = StorageByKeyName(Credentials, user_id, 'credentials').get()
        if credentials:
            service = self.getYoutube(user_id, credentials)
            if is_html:
                self_channel = service.channels().list(part='snippet', mine=True).execute()
                template_values = {
                    'google_login_url': users.create_login_url(self.request.uri),
                    'google_logout_url': users.create_logout_url('/'),
                    'javascripts': [JQUERY_URL, '/js/playlists.js'],
                }
                if len(self_channel.get('items', [])):
                    template_values['user_snippet'] = self_channel['items'][0].get('snippet')
                template = JINJA_ENVIRONMENT.get_template('playlists.html')
                self.response.write(template.render(template_values))
            else:
                # json method
                rv = playlists(service)
                self.response.out.write(json.dumps({
                        'code': 200,
                        'playlists': rv
                    }))
            self.saveCredentials(user_id, credentials)
            return None
    self.response.out.write(json.dumps({'code': 401, 'message': 'Unauthorized' }))

  def post(self, out_format):
    is_json = out_format.lower() == 'json'
    if not is_json:
        self.response.out.write(json.dumps({ 'code': 400, 'message': 'Bad request', }))
        return None
    user_id = self.session.get('user_id')
    if user_id:
        credentials = StorageByKeyName(Credentials, user_id, 'credentials').get()
        if credentials:
            service = self.getYoutube(user_id, credentials)
            blob = self.request.body
            try:
                pls = list(set(json.loads(blob)))
            except Exception, e:
                self.response.out.write(json.dumps({ 'code': 400, 'message': 'Bad request', }))
                return None
            rv = playlists(service, playlist_id=','.join(pls), part='contentDetails,snippet')
            self.response.out.write(json.dumps({
                    'code': 200,
                    'playlists': rv
                }))
            self.saveCredentials(user_id, credentials)
            return None
    self.response.out.write(json.dumps({'code': 401, 'message': 'Unauthorized' }))


class TasksHandler(BaseHandler):
  def getPlaylistId(self, data):
    if data.startswith('http://') or data.startswith('https://'):
        params = urlparse.parse_qs(urlparse.urlparse(data).query)
        data = params.get('list')[0]
    return data

  def getTasks(self):
    tasks = []
    user = users.get_current_user()
    if user and users.is_current_user_admin():
        for t in Tasks.query().order(Tasks.user_id):
            tasks.append(t)
    else:
        user_id = self.session.get('user_id')
        if user_id:
            for t in Tasks.query(Tasks.user_id == user_id):
                tasks.append(t)
    return tasks

  def worker(self, action):
    action = action.lower()
    user_id = self.session.get('user_id')
    if user_id:
        credentials = StorageByKeyName(Credentials, user_id, 'credentials').get()
        if credentials:
            if 'list' == action:
                tasks = self.getTasks()
                self.response.out.write(json.dumps({
                        'code': 200,
                        'tasks': convertTasks(tasks),
                    }))
            elif 'add' == action:
                source_playlist = self.getPlaylistId(self.request.get('source_playlist'))
                dest_playlist = self.getPlaylistId(self.request.get('dest_playlist'))
                playlist_prefix = self.request.get('playlist_prefix')
                if source_playlist is None:
                    self.response.out.write(json.dumps({ 'code': 400, 'message': 'Source playlist id format wrong or not setted.' }))
                    return
                tid = user_id + source_playlist
                t = Tasks.get_by_id(tid)
                if t is None:
                    tasks = self.getTasks()
                    t = Tasks(id=tid, user_id=user_id, source_playlist_id=source_playlist)
                    if dest_playlist:
                        service = self.getYoutube(user_id, credentials)
                        # TODO: need check if source_playlist and dest_playlist are youtube playlists and dest_playlist is user playlist
                        pl = playlists(service, playlist_id=dest_playlist)
                        if len(pl):
                            pl = pl[0]
                            self_channels = channels(service, part='id')
                            if pl.get('snippet', {}).get('channelId') in map(lambda el: el.get('id'), filter(lambda x: x.get('id'), self_channels)):
                                t.dest_playlist_id = dest_playlist
                            else:
                                self.response.out.write(json.dumps({ 'code': 400, 'message': 'You don\'t have premissions to change destination playlist' }))
                                return
                        else:
                            self.response.out.write(json.dumps({ 'code': 404, 'message': 'Destination playlist don\'t found' }))
                            return
                    if playlist_prefix:
                        t.playlist_title_prefix = playlist_prefix
                    t.put()
                    tasks.append(t)

                    taskqueue.add(url='/tasks/sync', params={'task_id': t.key.id() })

                    self.response.out.write(json.dumps({ 'code': 200, 'id': t.key.id(), 'tasks': convertTasks(tasks) }))
                else:
                    self.response.out.write(json.dumps({ 'code': 409, 'message': 'Task alredy in db', 'id': t.key.id(), }))
            elif 'delete' == action:
                tid = self.request.get('task_id')
                t = Tasks.get_by_id(tid)
                if t:
                    t.key.delete()
                    tasks = self.getTasks()
                    self.response.out.write(json.dumps({ 'code': 200, 'tasks': convertTasks(tasks), }))
                else:
                    self.response.out.write(json.dumps({ 'code': 404, 'message': 'Task not found', }))
            else:
                self.response.out.write(json.dumps({ 'code': 400, 'message': 'Bad request, list - get, add, delete - post', }))
            self.saveCredentials(user_id, credentials)
            return None
    self.response.out.write(json.dumps({'code': 401, 'message': 'Unauthorized' }))

  def get(self, action):
    self.worker(action)

  def post(self, action):
    self.worker(action)


class MainHandler(BaseHandler):
    def get(self):
        user_id = self.session.get('user_id')
        if user_id:
            credentials = StorageByKeyName(Credentials, user_id, 'credentials').get()
            if credentials:
                service = self.getYoutube(user_id, credentials)
                template_values = {
                    'user': users.get_current_user(),
                    'google_login_url': users.create_login_url(self.request.uri),
                    'google_logout_url': users.create_logout_url('/'),
                    'javascripts': [JQUERY_URL, JQUERY_UI_URL, '/js/app.js'],
                    'css': [JQUERY_UI_CSS, ],
                }
                self_channels = channels(service)
                if len(self_channels):
                    template_values['user_snippet'] = self_channels[0].get('snippet')
                template = JINJA_ENVIRONMENT.get_template('index.html')
                self.response.write(template.render(template_values))
                self.saveCredentials(user_id, credentials)
                return
        template_values = {
            'javascripts': (JQUERY_URL, ),
        }
        template = JINJA_ENVIRONMENT.get_template('index_unauth.html')
        self.response.write(template.render(template_values))
        return 


app = webapp2.WSGIApplication([
                               ('/', MainHandler),
                               ('/oauth2callback', OAuthHandler),
                               ('/youtube_(auth|logout)', YoutubeRedirectHandler),
                               ('/playlists.(json|html)', PlaylistsHandler),
                               ('/tasks/(list|add|delete).json', TasksHandler),
                               ('/tasks/sync', SyncPlaylistHandler),
                               ('/tasks/sync_from_cron', SyncPlaylistCronHandler),
                              ], debug=True, config=config)
