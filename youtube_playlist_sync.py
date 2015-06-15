#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webapp2
import jinja2
import os

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)+'/templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
decorator = appengine.OAuth2DecoratorFromClientSecrets('client_secrets.json', scope=YOUTUBE_READ_WRITE_SCOPE)

class YouPlaylistSyncHandler(webapp2.RequestHandler):
    @decorator.oauth_required
    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('youtube_playlist_sync.html')
        self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
                               ('/youtube_playlist_sync.html', YouPlaylistSyncHandler)
                              ], debug=True)
