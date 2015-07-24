
import json
import requests
import sys
from collections import deque
import threading
import time

DEFAULT_RETURN_ON = ['login', 'logout', 'play', 'pause', 'error', 'ap']

class SpotifyRemote(object):

    def __init__(self, port=None):
        self.port_start = 4370
        self.port_end = 4400
        if port:
            self.port = port
        else:
            self.port = self.port_start
        self.session = requests.Session()
        self.url_form = 'http://localhost.spotilocal.com:{0}{1}'
        self.paths = {
                'play': '/remote/play.json',
                'pause': '/remote/pause.json',
                'status': '/remote/status.json',
                'csrf': '/simplecsrf/token.json'
            }
        self.song_thread = QueueThread(self)

    def _call(self, path, headers=None, authed=False, **params):
        if authed:
            params['oauth'] = self.oauth_token
            params['csrf'] = self.csrf_token

        while self.port <= self.port_end:
            try:
                url = self.url_form.format(self.port, path)
                res = self.session.get(url, headers=headers, params=params, timeout=1)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                self.port += 1
        if self.port > self.port_end:
            print('Could not connect to spotify client')
            sys.exit(1)

        try:
            res_json = res.json()
        except ValueError as err:
            print(res)
            sys.exit(1)

        return res_json
        

    def setup(self):
        headers = dict(Origin='https://open.spotify.com')
        res = self._call(self.paths['csrf'], headers=headers)
        self.csrf_token = res.get('token')
        res = self.session.get('http://open.spotify.com/token')
        self.oauth_token = res.json().get('t')
        self.song_thread.start()

    def pause(self, pause=True):
        self._call(self.paths['pause'], authed=True, pause=str(pause).lower())

    def play(self, song_uri):
        self._call(self.paths['play'], authed=True, uri=song_uri, context=song_uri)

    def status(self):
        return self._call(self.paths['status'], authed=True, returnafter=1)

    def queue_song(self, song_uri):
        self.song_thread.queue_song(song_uri)


class QueueThread(threading.Thread):

    def __init__(self, spot_remote):
        threading.Thread.__init__(self)
        self.song_queue = deque()
        self.running = True
        self.remote = spot_remote
    
    def run(self):
        while self.running:
            if not self.remote.status()['playing'] and len(self.song_queue) > 0:
                print('setting song')
                self.remote.play(self.song_queue.pop())
            time.sleep(5)
    def queue_song(self, song_uri):
        self.song_queue.appendleft(song_uri)

spotify = SpotifyRemote(4381)
spotify.setup()

