# Leanback (plugin.video.leanback)

A Kodi video add-on that browses YouTube with the TV layout: the TV sidebar, shelves,
subscriptions, library and search, full video information, and DASH/HLS playback through
InputStream Adaptive. It targets Kodi 21 (Omega) and later.

## Features

- **Menus:** the TV guide entries (Search, Home, Shorts, Subscriptions, Library and topics),
  channel pages, playlists, related videos and paging.
- **Sign-in:** TV device code, with multiple accounts and an optional "Who's watching?" prompt.
- **Playback:** a DASH manifest built from direct stream URLs, HLS for live streams, captions
  plus auto-translated tracks, and the Shorts feed as a playlist.
- **Customisation:** show, hide or reorder main-menu items, pin channels, hide Shorts or
  watched videos, and set preferred quality, codec, HDR and audio track.

## Paths shared with other YouTube add-ons

Leanback also accepts the plugin paths other YouTube add-ons use, so `.strm` files, favourites and keymaps
written for them work after changing only the add-on id:

| Path | Opens |
|---|---|
| `/play/?video_id=ID` (`&seek=` or `&start=` seconds) | the video |
| `/play/?playlist_id=ID` (`&order=default\|reverse\|shuffle`, `&video_id=` first video) | the playlist, playing |
| `/channel/UC…/` | the channel |
| `/playlist/ID/`, `/channel/…/playlist/ID/` | the playlist |
| `/channel/mine/playlists/`, `/special/saved_playlists/` | your playlists |
| `/special/related_videos/?video_id=ID` | related videos |
| `/special/recommendations/` | Home |
| `/special/my_subscriptions/` | the Subscriptions feed |
| `/subscriptions/list/` | subscribed channels |
| `/search/?q=…`, `/kodion/search/query/?q=…` | search results |
| `/kodion/search/input/`, `/kodion/search/list/`, `/kodion/search/remove/?q=…` | new search, search history, remove a search |
| `/kodion/playback_history/` | your YouTube history |
| `/kodion/watch_later/list/` | Watch later |
| `/sign/in/`, `/sign/out/` | sign in, sign out |
| `/config/youtube/` | Leanback's settings |

## Development

```sh
pip install -r requirements-dev.txt
ruff check .
pytest
```

To build an installable zip for Kodi's **Install from zip file**:

```sh
python scripts/package.py
```

This writes `dist/plugin.video.leanback-<version>.zip`, with the version taken from `addon.xml`.

## License

GPL-3.0-only. See [LICENSE](LICENSE).
