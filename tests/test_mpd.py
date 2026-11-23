import xml.etree.ElementTree as ET

from resources.lib.youtube import mpd

NS = {'d': 'urn:mpeg:dash:schema:mpd:2011'}


def fmt(itag, mime, height=None, hdr=False, url=True, **extra):
    data = {'itag': itag, 'mimeType': mime, 'bitrate': 1000 * itag,
            'initRange': {'start': '0', 'end': '100'}, 'indexRange': {'start': '101', 'end': '200'},
            'approxDurationMs': '60000'}
    if url:
        data['url'] = 'https://rr1.googlevideo.com/videoplayback?itag=%d&a=1' % itag
    if height:
        data.update(width=height * 16 // 9, height=height, fps=30)
    if hdr:
        data['colorInfo'] = {'transferCharacteristics': 'COLOR_TRANSFER_CHARACTERISTICS_SMPTEST2084'}
    data.update(extra)
    return data


FORMATS = [
    fmt(137, 'video/mp4; codecs="avc1.640028"', 1080),
    fmt(248, 'video/webm; codecs="vp9"', 1080),
    fmt(313, 'video/webm; codecs="vp9"', 2160),
    fmt(337, 'video/webm; codecs="vp09.02.51.10.01.09.16.09.00"', 2160, hdr=True),
    fmt(399, 'video/mp4; codecs="av01.0.08M.08"', 1080),
    fmt(18, 'video/mp4; codecs="avc1.42001E, mp4a.40.2"', 360, url=False),  # muxed, no URL: skipped
    fmt(140, 'audio/mp4; codecs="mp4a.40.2"', audioChannels=2),
    fmt(251, 'audio/webm; codecs="opus"', audioChannels=2),
]


def test_select_video_caps_height_and_prefers_codec():
    heights = {f['height'] for f in mpd.select_video(FORMATS, max_height=1080)}
    assert heights == {1080}
    vp9 = mpd.select_video(FORMATS, codec='vp9')
    assert {mpd.codec_family(mpd._mime_codec(f)[1]) for f in vp9} == {'vp9'}
    # Unavailable codec preference falls back to everything.
    assert len(mpd.select_video([FORMATS[0]], codec='av01')) == 1


def test_select_video_can_drop_hdr():
    assert 337 in [f['itag'] for f in mpd.select_video(FORMATS)]
    assert 337 not in [f['itag'] for f in mpd.select_video(FORMATS, allow_hdr=False)]


def test_build_produces_valid_manifest():
    player = {'streamingData': {'adaptiveFormats': FORMATS}, 'videoDetails': {'lengthSeconds': '60'}}
    subs = [{'lang': 'en', 'label': 'English', 'kind': '', 'url': 'http://127.0.0.1:1/sub/x/0.vtt'}]
    root = ET.fromstring(mpd.build(player, max_height=2160, subtitles=subs))
    sets = root.findall('d:Period/d:AdaptationSet', NS)
    types = [s.get('contentType') for s in sets]
    assert types.count('video') == 4  # avc1, vp9, vp9 HDR, av01
    assert types.count('audio') == 2
    assert types.count('text') == 1
    hdr = [s for s in sets if s.find('d:SupplementalProperty', NS) is not None]
    assert len(hdr) == 1 and hdr[0].find('d:SupplementalProperty', NS).get('value') == '16'
    base = root.find('.//d:Representation[@id="137"]/d:BaseURL', NS).text
    assert base.endswith('itag=137&a=1')  # & escaped in XML, intact once parsed
    assert root.find('.//d:Representation[@id="18"]', NS) is None
    assert root.get('mediaPresentationDuration') == 'PT60.000S'


def test_build_without_audio_returns_none():
    assert mpd.build({'streamingData': {'adaptiveFormats': FORMATS[:2]}}) is None


def test_audio_default_follows_preference():
    dubbed = [
        fmt(140, 'audio/mp4; codecs="mp4a.40.2"',
            audioTrack={'id': 'en.4', 'displayName': 'English original', 'audioIsDefault': True}),
        fmt(141, 'audio/mp4; codecs="mp4a.40.2"',
            audioTrack={'id': 'de.3', 'displayName': 'German', 'audioIsDefault': False}),
    ]
    player = {'streamingData': {'adaptiveFormats': [FORMATS[0]] + dubbed}}

    def default_lang(**kwargs):
        root = ET.fromstring(mpd.build(player, **kwargs))
        return [s.get('lang') for s in root.findall('.//d:AdaptationSet[@contentType="audio"]', NS)
                if s.get('default') == 'true']

    assert default_lang(audio_pref='original') == ['en']
    assert default_lang(audio_pref='kodi', ui_lang='de') == ['de']


def captions(tracks, translations=('de', 'fr')):
    return {'captions': {'playerCaptionsTracklistRenderer': {
        'captionTracks': tracks,
        'translationLanguages': [{'languageCode': c, 'languageName': {'simpleText': c.upper()}}
                                 for c in translations]}}}


def test_subtitle_tracks_native_asr_and_translation():
    player = captions([
        {'baseUrl': 'https://www.youtube.com/api/timedtext?v=x&lang=en', 'languageCode': 'en',
         'name': {'simpleText': 'English'}},
        {'baseUrl': 'https://www.youtube.com/api/timedtext?v=x&lang=en&kind=asr', 'languageCode': 'en',
         'kind': 'asr', 'name': {'simpleText': 'English (auto-generated)'}},
    ])
    subs = mpd.subtitle_tracks(player, include_asr=True, translate_to=['en', 'de', 'xx'])
    assert [(s['lang'], s['kind']) for s in subs] == [('en', ''), ('en', 'asr'), ('de', 'translated')]
    assert subs[2]['url'].endswith('lang=en&fmt=vtt&tlang=de')  # translated from the native track
    without_asr = mpd.subtitle_tracks(player, include_asr=False, translate_to=[])
    assert [s['kind'] for s in without_asr] == ['']


def test_subtitle_tracks_none_without_captions():
    assert mpd.subtitle_tracks({}) == []
