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

## Development

```sh
pip install -r requirements-dev.txt
ruff check .
pytest
```

## License

GPL-3.0-only. See [LICENSE](LICENSE).
