import threading
from typing import List, Union
from .track import Track
from .utils.errors import TrackNotExist

__all__ = ('Playlist',)

class Playlist:
    """a class representing playlist for tracks

    This class is thread-safe.
    """
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

    def add_track(self, track: Track) -> None:
        """Add a track
        
        Parameters
        -----------
        track: :class:`Track`
            The audio track that we want to put in playlist.
        """
        with self._lock:
            self._put(track)

    def jump_to_pos(self, pos: int) -> Track:
        """Change playlist pos and return :class:`Track` from given position
        
        Parameters
        -----------
        pos: :class:`int`
            Track position that we want jump to

        Raises
        -------
        TrackNotExist
            Given track position is not exist

        Returns
        --------
        :class:`Track`
            The audio track from given position
        """
        with self._lock:
            track = self.get_track_from_pos(pos)
            raw_track = self._get_raw_track(track)
            self._pos = raw_track['_id']
        return track

    def remove_track(self, track: Track) -> None:
        """Remove a track
        
        Parameters
        -----------
        track: :class:`Track`
            The audio track that we want to remove from playlist.

        Raises
        -------
        TrackNotExist
            Given track is not exist
        """
        with self._lock:
            self._remove(track)

    def remove_track_from_pos(self, pos: int) -> None:
        """Remove a track from given position
        
        Parameters
        -----------
        pos: :class:`int`
            Track position that we want remove from playlist

        Raises
        -------
        TrackNotExist
            Given track position is not exist
        """
        with self._lock:
            track = self.get_track_from_pos(pos)
            self._remove(track)
    
    def remove_all_tracks(self) -> None:
        """Remove all tracks from playlist"""
        with self._lock:
            self._tracks = []
            self._pos = 0

    def reset_pos_tracks(self) -> None:
        """Reset current position playlist"""
        with self._lock:
            self._pos = 0

    def is_track_exist(self, track: Track) -> bool:
        """Check if given track is exist in this playlist
        
        Parameters
        -----------
        track: :class:`Track`
            The audio track that we want to check
        
        Returns
        --------
        :class:`bool`
            `True` if exist, or `False` if not exist
        """
        t = self._get_raw_track(track)
        return t != None
    
    def get_all_tracks(self) -> List[Track]:
        """Get all tracks in this playlist
        
        Returns
        --------
        List[:class:`Track`]
            All tracks in playlist
        """
        return [t['track'] for t in self._tracks]

    def get_current_track(self) -> Track:
        """Get current track in current position
        
        Returns
        --------
        :class:`Track`
            The current track in current position
        """
        return self.get_track_from_pos(self._pos)

    def get_track_from_pos(self, pos: int) -> Track:
        """Get a track from given position
        
        Parameters
        -----------
        pos: :class:`int`
            Track position that we want remove from playlist

        Raises
        -------
        TrackNotExist
            Given track position is not exist

        Returns
        --------
        :class:`Track`
            The track from given position
        """
        try:
            t = self._tracks[pos]
        except IndexError:
            raise TrackNotExist('track position %s is not exist' % pos) from None
        else:
            return t['track']

    def get_next_track(self) -> Union[Track, None]:
        """Get next track
        
        Returns
        --------
        Union[:class:`Track`, None]
            The next track of this playlist
        """
        with self._lock:
            try:
                t = self._tracks[self._pos + 1]
            except IndexError:
                return None
            else:
                self._pos += 1
                return t['track']

    def get_previous_track(self) -> Union[Track, None]:
        """Get previous track
        
        Returns
        --------
        Union[:class:`Track`, None]
            The previous track of this playlist
        """
        with self._lock:
            try:
                t = self._tracks[self._pos - 1]
            except IndexError:
                return None
            else:
                self._pos -= 1
                return t['track']