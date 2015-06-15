#!/usr/bin/python
# -*- coding: utf-8 -*-

__version__ = '0.1'
__author__ = 'Andrey Derevyagin'
__copyright__ = 'Copyright © 2015'

import httplib2
import os
import sys

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
import logging

import json


def create_playlist(youtube, title, description=None, privacyStatus='private'):
    # This code creates a new, private playlist in the authorized user's channel.
    snippet = {
        'title': title
    }
    if description:
        snippet['description'] = description
    playlists_insert_response = youtube.playlists().insert(
        part="snippet,status",
        body=dict(
            snippet=snippet,
        status=dict(
            privacyStatus=privacyStatus
          )
        )
    ).execute()

    return playlists_insert_response

def channels(youtube, channel_ids=None, part='snippet'):
    rv = []
    if channel_ids is None:
        channels_list_request = youtube.channels().list(part=part, mine=True, maxResults=50)
    else:
        channels_list_request = youtube.channels().list(part=part, maxResults=50, id=channel_ids)
    while channels_list_request:
        channels_list_response = channels_list_request.execute()
        rv.extend(channels_list_response.get('items', []))
        channels_list_request = youtube.channels().list_next(channels_list_request, channels_list_response)
    return rv


def playlists(youtube, playlist_id=None, part='snippet'):
    '''
        return self user playlists if playlist_id is not setted
        playlist_id can by a comma-separated list of the YouTube playlist ID(s).
    '''
    rv = []
    if playlist_id is None:
        playlists_list_request = youtube.playlists().list(part=part, mine=True, maxResults=50)
    else:
        playlists_list_request = youtube.playlists().list(part=part, maxResults=50, id=playlist_id)
    while playlists_list_request:
        playlists_list_response = playlists_list_request.execute()
        for pl in playlists_list_response.get('items', []):
            rv.append(pl)
        playlists_list_request = youtube.playlists().list_next(playlists_list_request, playlists_list_response)
    return rv

def playlist_items(youtube, playlist_id):
    # Retrieve the list of videos uploaded to the authenticated user's channel.
    rv = []
    playlistitems_list_request = youtube.playlistItems().list(
        playlistId=playlist_id,
        part="snippet",
        maxResults=50)
    while playlistitems_list_request:
        playlistitems_list_response = playlistitems_list_request.execute()
        for playlist_item in playlistitems_list_response["items"]:
            rv.append(playlist_item)
        playlistitems_list_request = youtube.playlistItems().list_next(playlistitems_list_request, playlistitems_list_response)
    return rv

def playlist_insert_resource(youtube, playlist_id, resource_id=None, video_id=None, position=None):
    if (resource_id is None) ^ (video_id is None):
        body = {
            'snippet': {
                'playlistId': playlist_id
            },
            #'kind': 'youtube#playlistItem'
        }
        if resource_id:
            body['snippet']['resourceId'] = resource_id
        else:
            body['snippet']['resourceId'] = {
                'kind': 'youtube#video',
                'videoId': video_id
            }
        if position is not None:
            body['snippet']['position'] = position
        return youtube.playlistItems().insert(part="snippet", body=body).execute()
    else:
        logging.error('Setted both or nothing "resource_id", "video_id"')

def playlist_serch_or_create(youtube, playlist_title):
    playlist_arr = playlists(youtube)
    playlist_info = None
    for pl in playlist_arr:
        if playlist_title == pl.get('snippet', {}).get('title'):
            playlist_info = pl
            break
    if playlist_info is None:
        playlist_info = create_playlist(youtube, title=playlist_title, description='Created by youtube-sync service.', privacyStatus='unlisted')
    return playlist_info

def playlist_sync(youtube, source_playlist_id, dest_playlist_id=None):
    source_playlist_info = playlists(youtube, playlist_id=source_playlist_id)
    if len(source_playlist_info) == 0:
        return -1
    source_playlist_info = source_playlist_info[0]

    if dest_playlist_id:
        dest_playlist_info = playlists(youtube, playlist_id=dest_playlist_id)
        if len(dest_playlist_info) == 0:
            return -2
        dest_playlist_info = dest_playlist_info[0]

    else:
        title = source_playlist_info.get('snippet', {}).get('title')
        dest_playlist_info = playlist_serch_or_create(youtube, title)
        if dest_playlist_info is None:
            return -3
    source_items_tmp = playlist_items(youtube, source_playlist_info['id'])
    dest_items = playlist_items(youtube, dest_playlist_info['id'])

    # delete all deleted videos and fix positions
    source_items = []
    for itm in source_items_tmp:
        if not itm.get('snippet', {}).has_key('thumbnails'):
            continue
        itm['snippet']['position'] = len(source_items)
        source_items.append(itm)
    source_resourceId = map(lambda el: el.get('snippet', {}).get('resourceId'), source_items)
    dest_resourceId = map(lambda el: el.get('snippet', {}).get('resourceId'), dest_items)
    for itm in dest_items:
        if itm.get('snippet', {}).get('resourceId') not in source_resourceId:
            logging.info('Delete video: %s', itm.get('snippet', {}).get('resourceId'))

            response = youtube.playlistItems().delete(id=itm.get('id')).execute()
    for itm in source_items:
        itm_resourceId = itm.get('snippet', {}).get('resourceId')
        itm_pos = itm.get('snippet', {}).get('position')
        if itm_resourceId not in dest_resourceId:
            pos = None
            if itm_pos < len(dest_resourceId):
                pos = itm_pos
                logging.info('Insert video: %s in position %s', itm_resourceId, pos)
            playlist_insert_resource(youtube, dest_playlist_info.get('id'), resource_id=itm_resourceId, position=pos)
            if pos:
                dest_resourceId.insert(pos, itm_resourceId)
            else:
                dest_resourceId.append(itm_resourceId)
        else:
            tmp_itm = filter(lambda el: el.get('snippet', {}).get('resourceId')==itm_resourceId, dest_items)
            if len(tmp_itm) == 0:
                logging.error('Error in search playlist item %s', itm)
                continue
            tmp_itm = tmp_itm[0]
            if tmp_itm.get('snippet', {}).get('position') != itm_pos:
                body = {
                    'id': tmp_itm.get('id'),
                    'snippet': {
                        'playlistId': dest_playlist_info.get('id'),
                        'resourceId': tmp_itm.get('snippet', {}).get('resourceId'),
                        'position': itm_pos
                    }
                }
                logging.info('Change position: %s', tmp_itm.get('snippet', {}).get('resourceId'))
                response = youtube.playlistItems().update(part="snippet", body=body).execute()
    return 0

def video_info(youtube, video_id):
    #video_response = youtube.videos().list(id=video_id, part='snippet, recordingDetails').execute()
    video_response = youtube.videos().list(id=video_id, part='id, snippet, contentDetails, player, statistics, recordingDetails, status, topicDetails').execute()
    #print json.dumps(video_response)
    return video_response


if __name__=='__main__':
    # The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
    # the OAuth 2.0 information for this application, including its client_id and
    # client_secret. You can acquire an OAuth 2.0 client ID and client secret from
    # the Google Developers Console at
    # https://console.developers.google.com/.
    # Please ensure that you have enabled the YouTube Data API for your project.
    # For more information about using OAuth2 to access the YouTube Data API, see:
    #   https://developers.google.com/youtube/v3/guides/authentication
    # For more information about the client_secrets.json file format, see:
    #   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
    CLIENT_SECRETS_FILE = "client_secrets.json"

    # This variable defines a message to display if the CLIENT_SECRETS_FILE is
    # missing.
    MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

    # This OAuth 2.0 access scope allows for full read/write access to the
    # authenticated user's account.
    YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"


    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
        message=MISSING_CLIENT_SECRETS_MESSAGE,
        scope=YOUTUBE_READ_WRITE_SCOPE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        flags = argparser.parse_args()
        credentials = run_flow(flow, storage, flags)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))


    playlists = playlists(youtube)
    print json.dumps(playlists)

