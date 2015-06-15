# YouTube Playlist sync service

Simple service for syncing YouTube playlists between youtube accounts. This service working on Google AppEngine.

## Prepare before deploy on GAE

- On project directory install [google-api-python-client](https://github.com/google/google-api-python-client) following command:
`pip install --target=lib -r requirements.txt`
- Create you own application on [Google developers console](https://console.developers.google.com) and grant permissions to use YouTube API.
- Rename "settings.py.template" to "settings.py" and fill app keys and constants.
- Raname on 'app.yaml' application name.

Now you can deploy project on GAE.

Working [app](http://youtube-playlist-sync.appspot.com).

## Licensing

YouTube sync is licensed under MIT License Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.