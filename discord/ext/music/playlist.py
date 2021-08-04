import threading
from typing import List, Union
from .track import Track
from .utils.errors import TrackNotExist

class Playlist:
    """a class representing playlist for tracks"""
    def __init__(self) -> None:
        self._tracks = []
        self._lock = threading.Lock()
        self._pos = 0

    def _reorder_id_tracks(self, tracks):
        num = 0
        for t in tracks:
            t['_id'] = num
            num += 1

    def _put(self, track):
        t = {
            "_id": len(self._tracks),
            "track": track
        }
        self._tracks.append(t)
        self._reorder_id_tracks(self._tracks)

    def _get_raw_track(self, track):
        target = None
        for t in self._tracks:
            if t['track'] == track:
                target = t
        return target

    def _remove(self, track):
        target = self._get_raw_track(track)
        if target is None:
            raise TrackNotExist('track is not exist')
        self._tracks.remove(target)
        self._reorder_id_tracks(self._tracks)

    def insert_track(self, track: Track):
        with self._lock:
            self._put(track)

    def remove_track(self, track: Track):
        with self._lock:
            self._remove(track)
    
    def remove_all_tracks(self):
        with self._lock:
            self._tracks = []
            self._pos = 0

    def reset_pos_tracks(self):
        with self._lock:
            self._pos = 0

    def is_track_exist(self, track: Track) -> bool:
        t = self._get_raw_track(track)
        return t != None
    
    def get_all_tracks(self) -> List[Track]:
        return [t['track'] for t in self._tracks]

    def get_track(self, track: Track):
        target = self._get_raw_track(track)
        if target is None:
            raise TrackNotExist('track is not exist')
        return target['track']

    def get_next_track(self) -> Union[Track, None]:
        with self._lock:
            try:
                t = self._tracks[self._pos + 1]
            except IndexError:
                return None
            else:
                self._pos += 1
                return t

    def get_previous_track(self) -> Union[Track, None]:
        with self._lock:
            try:
                t = self._tracks[self._pos - 1]
            except IndexError:
                return None
            else:
                self._pos -= 1
                return t