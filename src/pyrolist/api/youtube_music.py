import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from loguru import logger
from pyrolist.config.settings import AppSettings
from pyrolist.config.paths import AppDirs

class YouTubeMusicClient:
    """Hybrid YouTube client - uses ytmusicapi for browsing, yt-dlp as fallback."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="ytm")
        self._stream_cache = {}
        self._search_cache = {}
        self._search_time = {}
        self._ytmusicapi = None          # authenticated instance (for library)
        self._ytmusicapi_public = None   # unauthenticated instance (for search/home/charts)
        self._is_authenticated = False
        self._init_public_client()
        self._load_auth_session()

    def _init_public_client(self):
        """Initialize an unauthenticated ytmusicapi for public operations."""
        try:
            from ytmusicapi import YTMusic
            self._ytmusicapi_public = YTMusic()
            logger.debug("ytmusicapi public client initialized")
        except Exception as e:
            logger.warning(f"Failed to init public ytmusicapi: {e}")

    def _load_auth_session(self):
        """Load auth session from browser cookies (headers_auth.json)."""
        auth_file = AppDirs.config / "headers_auth.json"
        
        if auth_file.exists():
            try:
                self._setup_ytmusicapi(str(auth_file))
                logger.info("ytmusicapi initialized from browser cookies (headers_auth.json)")
            except Exception as e:
                logger.error(f"Failed to load browser cookies: {e}")
                self._is_authenticated = False

    def _setup_ytmusicapi(self, auth_path: str):
        """Setup ytmusicapi with the given auth file."""
        try:
            from ytmusicapi import YTMusic
            
            # Browser auth (cookie)
            self._ytmusicapi = YTMusic(auth=auth_path)
                
            self._is_authenticated = True
        except Exception as e:
            logger.error(f"Failed to setup ytmusicapi: {e}")
            self._is_authenticated = False

    @property
    def _public(self):
        """Returns the unauthenticated ytmusicapi instance for public queries.
        Always use the public client for search/home/charts since
        Desktop OAuth credentials cause HTTP 400 with ytmusicapi's internal API."""
        return self._ytmusicapi_public

    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated

    def load_existing_auth(self) -> bool:
        return self._is_authenticated

    def reload_auth(self):
        """Reload the ytmusicapi instance with new credentials."""
        self._load_auth_session()

    def get_cached_stream_url(self, video_id: str) -> str:
        return self._stream_cache.get(video_id, "")

    async def _run(self, func):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, func)

    async def authenticate_with_oauth(self) -> bool:
        """Trigger OAuth PKCE flow and setup ytmusicapi."""
        from pyrolist.api.oauth_pkce import OAuthPKCE

        oauth = OAuthPKCE()

        def run_oauth():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(oauth.authenticate())
                return result
            finally:
                loop.close()

        success = await self._run(run_oauth)

        if success and AppDirs.oauth_file.exists():
            self._load_oauth_tokens()

        return success

    async def search(self, query: str, filter: str = None, limit: int = 20) -> list:
        """Search using ytmusicapi (public, no auth needed), fallback to yt-dlp."""
        query_lower = query.lower().strip()
        cache_key = f"{query_lower}:{filter}:{limit}"

        if cache_key in self._search_cache:
            age = time.time() - self._search_time.get(cache_key, 0)
            if age < 300:
                logger.debug(f"Using cached search for '{query_lower}'")
                return self._search_cache[cache_key]

        # Try ytmusicapi first (richer results with types)
        client = self._ytmusicapi if (self._is_authenticated and self._ytmusicapi) else self._public
        if client:
            def _ytm_search():
                try:
                    return client.search(query_lower, filter=filter, limit=limit)
                except Exception as e:
                    logger.warning(f"ytmusicapi search failed: {e}")
                    return None

            try:
                results = await self._run(_ytm_search)
                if results:
                    self._search_cache[cache_key] = results
                    self._search_time[cache_key] = time.time()
                    for track in results[:3]:
                        vid = track.get('videoId')
                        if vid:
                            asyncio.create_task(self._prefetch_stream(vid))
                    return results
            except Exception:
                pass

        # Fallback to yt-dlp
        def _ytdlp_search():
            opts = {
                'quiet': True,
                'no_warnings': True,
                'default_search': f'ytsearch{limit}',
                'skip_download': True,
                'ignoreerrors': True,
            }
            try:
                ydl = yt_dlp.YoutubeDL(opts)
                results = ydl.extract_info(query_lower, download=False)
                if not results or not results.get('entries'):
                    return []
                tracks = []
                for entry in results['entries']:
                    if not entry:
                        continue
                    video_id = entry.get('id', '')
                    if video_id and entry.get('title'):
                        thumbnails = entry.get('thumbnails', [])
                        thumb_url = thumbnails[-1].get('url', '') if thumbnails else ''
                        tracks.append({
                            'videoId': video_id,
                            'title': entry.get('title', 'Unknown'),
                            'artists': [{'name': entry.get('uploader', 'Unknown')}],
                            'thumbnails': [{'url': thumb_url}] if thumb_url else [],
                            'duration': entry.get('duration', 0),
                            'resultType': 'song',
                        })
                return tracks
            except Exception as e:
                logger.error(f"yt-dlp search error: {e}")
                return []

        try:
            tracks = await self._run(_ytdlp_search)
            if tracks:
                self._search_cache[cache_key] = tracks
                self._search_time[cache_key] = time.time()
            return tracks
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def _prefetch_stream(self, video_id: str):
        if video_id in self._stream_cache:
            return
        try:
            from pyrolist.api.stream_extractor import StreamExtractor
            extractor = StreamExtractor(self.settings)
            result = await extractor.get_stream_info(video_id)
            url = result.get("url", "")
            if url:
                self._stream_cache[video_id] = url
                logger.debug(f"Prefetched stream for {video_id}")
        except Exception as e:
            pass

    async def get_stream_url(self, video_id: str) -> str:
        if video_id in self._stream_cache:
            return self._stream_cache[video_id]
        try:
            from pyrolist.api.stream_extractor import StreamExtractor
            extractor = StreamExtractor(self.settings)
            result = await extractor.get_stream_info(video_id)
            url = result.get("url", "")
            if url:
                self._stream_cache[video_id] = url
            return url
        except:
            return ""

    async def get_library_songs(self, limit: int = 25) -> dict:
        """Get user's liked songs - requires auth."""
        if not self._is_authenticated or not self._ytmusicapi:
            return {'tracks': []}

        def _get_liked():
            try:
                result = self._ytmusicapi.get_liked_songs(limit=limit)
                # ytmusicapi already returns {'tracks': [...], ...}
                return result
            except Exception as e:
                logger.error(f"get_liked_songs error: {e}")
                return {'tracks': []}

        try:
            return await self._run(_get_liked)
        except Exception as e:
            logger.error(f"Library songs error: {e}")
            return {'tracks': []}

    async def get_library_playlists(self) -> list:
        """Get user's playlists - requires auth."""
        if not self._is_authenticated or not self._ytmusicapi:
            return []

        def _get_playlists():
            try:
                return self._ytmusicapi.get_library_playlists()
            except Exception as e:
                logger.error(f"get_playlists error: {e}")
                return []

        try:
            return await self._run(_get_playlists)
        except:
            return []

    async def get_library_albums(self) -> list:
        """Get user's albums - requires auth."""
        if not self._is_authenticated or not self._ytmusicapi:
            return []

        def _get_albums():
            try:
                return self._ytmusicapi.get_library_albums()
            except Exception as e:
                logger.error(f"get_albums error: {e}")
                return []

        try:
            return await self._run(_get_albums)
        except:
            return []

    async def get_library_artists(self) -> list:
        """Get user's subscribed artists - requires auth."""
        if not self._is_authenticated or not self._ytmusicapi:
            return []

        def _get_artists():
            try:
                return self._ytmusicapi.get_library_artists()
            except Exception as e:
                logger.error(f"get_library_artists error: {e}")
                return []

        try:
            return await self._run(_get_artists)
        except:
            return []

    async def get_liked_songs(self, limit: int = 25) -> dict:
        """Get liked songs - wrapper for library."""
        return await self.get_library_songs(limit)

    async def get_home(self, limit: int = 10) -> dict:
        """Get home recommendations - uses auth client if available."""
        client = self._ytmusicapi if self._is_authenticated else self._public
        if not client:
            return {'contents': []}

        def _get_home():
            try:
                return client.get_home(limit=limit)
            except Exception as e:
                logger.error(f"get_home error: {e}")
                return {'contents': []}

        try:
            return await self._run(_get_home)
        except:
            return {'contents': []}

    async def get_explore(self) -> dict:
        """Get explore data - uses auth client if available."""
        client = self._ytmusicapi if self._is_authenticated else self._public
        if not client:
            return {'moodCategories': []}

        def _get_explore():
            try:
                return client.get_explore()
            except Exception as e:
                logger.error(f"get_explore error: {e}")
                return {'moodCategories': []}

        try:
            return await self._run(_get_explore)
        except:
            return {'moodCategories': []}

    async def get_charts(self, country: str = "ZZ") -> dict:
        """Get charts - uses auth client if available."""
        client = self._ytmusicapi if self._is_authenticated else self._public
        if not client:
            return {'items': []}

        def _get_charts():
            try:
                return client.get_charts(country=country)
            except Exception as e:
                logger.error(f"get_charts error: {e}")
                return {'items': []}

        try:
            return await self._run(_get_charts)
        except:
            return {'items': []}

    async def get_playlist(self, playlist_id: str) -> dict:
        """Get playlist details - uses public client."""
        client = self._public
        if not client:
            return {}

        def _get_playlist():
            try:
                return client.get_playlist(playlist_id)
            except Exception as e:
                logger.error(f"get_playlist error: {e}")
                return {}

        try:
            return await self._run(_get_playlist)
        except:
            return {}

    async def get_album(self, browse_id: str) -> dict:
        """Get album details - uses public client."""
        client = self._public
        if not client:
            return {}

        def _get_album():
            try:
                return client.get_album(browse_id)
            except Exception as e:
                logger.error(f"get_album error: {e}")
                return {}

        try:
            return await self._run(_get_album)
        except:
            return {}

    async def get_artist(self, channel_id: str) -> dict:
        """Get artist details - uses public client."""
        client = self._public
        if not client:
            return {}

        def _get_artist():
            try:
                return client.get_artist(channel_id)
            except Exception as e:
                logger.error(f"get_artist error: {e}")
                return {}

        try:
            return await self._run(_get_artist)
        except:
            return {}

    async def get_watch_playlist(self, video_id: str = None, limit: int = 25) -> dict:
        """Get watch playlist - requires auth."""
        if not self._is_authenticated or not self._ytmusicapi:
            return {'tracks': []}

        def _get_watch():
            try:
                return self._ytmusicapi.get_watch_playlist(videoId=video_id, limit=limit)
            except Exception as e:
                logger.error(f"get_watch_playlist error: {e}")
                return {'tracks': []}

        try:
            return await self._run(_get_watch)
        except:
            return {'tracks': []}

    async def get_history(self) -> list:
        """Get user's listening history - requires auth."""
        if not self._is_authenticated or not self._ytmusicapi:
            return []

        def _get_history():
            try:
                return self._ytmusicapi.get_history()
            except Exception as e:
                logger.error(f"get_history error: {e}")
                return []

        try:
            return await self._run(_get_history)
        except:
            return []

    async def remove_history_items(self, feedback_tokens: list) -> bool:
        """Remove items from user's listening history."""
        if not self._is_authenticated or not self._ytmusicapi:
            return False

        def _remove():
            try:
                # remove_history_items returns a dict or list usually
                self._ytmusicapi.remove_history_items(feedback_tokens)
                return True
            except Exception as e:
                logger.error(f"remove_history_items error: {e}")
                return False

        try:
            return await self._run(_remove)
        except:
            return False

    async def get_video_info(self, video_id: str) -> dict:
        return {}

    def logout(self) -> None:
        """Clear OAuth tokens and reset auth state."""
        if AppDirs.oauth_file.exists():
            AppDirs.oauth_file.unlink()
        self._ytmusicapi = None
        self._is_authenticated = False
        logger.info("Logged out of YouTube")

    async def search_suggestions(self, query: str) -> dict:
        """Get rich search suggestions - uses search API for top results."""
        if not self._public or not query:
            return {}

        def _get_rich_suggestions():
            try:
                # Search without filter to get a mix of top results
                results = self._public.search(query, limit=5)
                # Group by category
                grouped = {
                    'songs': [r for r in results if r['resultType'] in ('song', 'video')][:3],
                    'albums': [r for r in results if r['resultType'] == 'album'][:2],
                    'artists': [r for r in results if r['resultType'] == 'artist'][:2],
                    'text': []
                }
                # Also get standard text suggestions
                try:
                    grouped['text'] = self._public.get_search_suggestions(query)[:5]
                except:
                    pass
                return grouped
            except Exception as e:
                logger.error(f"Rich suggestions error: {e}")
                return {}

        try:
            return await self._run(_get_rich_suggestions)
        except:
            return {}