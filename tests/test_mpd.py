import os
import struct
import xml.etree.ElementTree as ET

import pytest

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


def test_select_video_caps_height_and_keeps_every_codec():
    heights = {f['height'] for f in mpd.select_video(FORMATS, max_height=1080)}
    assert heights == {1080}
    families = {mpd.codec_family(mpd._mime_codec(f)[1]) for f in mpd.select_video(FORMATS)}
    assert families == {'avc1', 'vp9', 'av01'}


def video_sets(**kwargs):
    root = ET.fromstring(mpd.build({'streamingData': {'adaptiveFormats': FORMATS}}, **kwargs))
    return [(s.find('d:Representation', NS).get('codecs').split('.')[0], s.get('default'),
             s.find('d:Role', NS).get('value'))
            for s in root.findall('.//d:AdaptationSet[@contentType="video"]', NS)]


def test_preferred_codec_is_the_first_and_default_video_set():
    """Every codec stays in the manifest, for ISA's Manual OSD and Ask quality; ISA starts on the preferred."""
    sets = video_sets(codec='av01')
    assert sets[0] == ('av01', 'true', 'main')
    assert {codec for codec, _, _ in sets} == {'avc1', 'vp9', 'vp09', 'av01'}
    assert all(default is None and role == 'alternate' for _, default, role in sets[1:])
    assert video_sets()[0][1:] == ('true', 'main')  # 'any': the tallest set leads


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


def test_select_audio_skips_stable_volume_copies():
    opus = 'audio/webm; codecs="opus"'
    plain = fmt(251, opus)
    drc = fmt(251, opus, isDrc=True)
    drc_url = dict(plain, url=plain['url'] + '&xtags=drc%3D1')
    drc_only = fmt(250, opus, isDrc=True)
    dub, dub_drc = (fmt(251, opus, audioTrack={'id': 'de.3'}, **extra) for extra in ({}, {'isDrc': True}))
    assert mpd.select_audio([plain, drc, drc_url, drc_only, dub, dub_drc]) == [plain, drc_only, dub]


def test_build_audio_has_one_representation_per_itag():
    audio = [fmt(251, 'audio/webm; codecs="opus"'), fmt(251, 'audio/webm; codecs="opus"', isDrc=True)]
    root = ET.fromstring(mpd.build({'streamingData': {'adaptiveFormats': [FORMATS[0]] + audio}}))
    assert len(root.findall('.//d:AdaptationSet[@contentType="audio"]/d:Representation[@id="251"]', NS)) == 1


def index_fixture(name):
    """The first 400 bytes of a real YouTube format's segment index (its sidx box: no addresses in it)."""
    with open(os.path.join(os.path.dirname(__file__), 'data', name), 'rb') as handle:
        return handle.read()


def sidx(timescale, durations, version=0):
    """A sidx box with these subsegment durations."""
    times = struct.pack('>II', 0, 0) if version == 0 else struct.pack('>QQ', 0, 0)
    refs = b''.join(struct.pack('>III', 1000, d, 0x90000000) for d in durations)
    body = bytes([version, 0, 0, 0]) + struct.pack('>II', 1, timescale) + times + \
        struct.pack('>HH', 0, len(durations)) + refs
    return struct.pack('>I', 8 + len(body)) + b'sidx' + body


@pytest.mark.parametrize('name, fps, kind', [
    ('sidx-23.976fps.bin', 24, 'ntsc'),  # timescale 24000, every segment a multiple of 1001
    ('sidx-60fps.bin', 60, 'whole'),  # timescale 15360, multiples of 256
    ('sidx-30fps.bin', 30, 'whole'),  # the same video's 30 fps formats, multiples of 512
    ('sidx-50fps.bin', 50, 'whole'),  # timescale 12800, multiples of 256
])
def test_rate_kind_from_real_indexes(name, fps, kind):
    assert mpd.rate_kind(index_fixture(name), fps) == (kind, '')


@pytest.mark.parametrize('timescale, step, fps, kind', [
    (24000, 1001, 24, 'ntsc'),  # 23.976
    (30000, 1001, 30, 'ntsc'),  # 29.97
    (60000, 1001, 60, 'ntsc'),  # 59.94
    (12288, 512, 24, 'whole'),
    (12800, 512, 25, 'whole'),
    (15360, 512, 30, 'whole'),
    (12800, 256, 50, 'whole'),
    (15360, 256, 60, 'whole'),
])
def test_rate_kind_for_each_rate(timescale, step, fps, kind):
    """Segments of a whole number of frames, some longer than others, as at scene cuts."""
    frames = [88, 162, 76, 120, 300, 45, 500, 133]
    assert mpd.rate_kind(sidx(timescale, [step * n for n in frames]), fps) == (kind, '')


def test_rate_kind_from_the_start_of_a_long_index():
    """A long video's index holds hundreds of entries; only the first SIDX_READ bytes are fetched."""
    long_ntsc = sidx(60000, [1001 * 300] * 900, version=1)[:mpd.SIDX_READ]
    assert mpd.rate_kind(long_ntsc, 60) == ('ntsc', '')
    long_whole = sidx(15360, [256 * 330] * 900, version=1)[:mpd.SIDX_READ]
    assert mpd.rate_kind(long_whole, 60) == ('whole', '')
    # an entry past the ones checked doesn't count, even if it would decide otherwise
    assert mpd.rate_kind(sidx(60000, [1001 * 300] * mpd.SIDX_REFS + [1500]), 60) == ('ntsc', '')


def test_rate_kind_checks_the_entries_that_arrived():
    """A count claiming more entries than the bytes hold: the ones there decide."""
    index = bytearray(sidx(30000, [1001 * 150] * 5))
    struct.pack_into('>H', index, 30, 500)  # v0 reference_count
    assert mpd.rate_kind(bytes(index), 30) == ('ntsc', '')
    assert mpd.rate_kind(bytes(index[:32]), 30) == (None, 'short index')  # a count but no entries


def test_rate_kind_reads_both_index_versions():
    assert mpd.rate_kind(sidx(24000, [88088, 162162]), 24) == ('ntsc', '')
    assert mpd.rate_kind(sidx(24000, [88088, 162162], version=1), 24) == ('ntsc', '')
    assert mpd.rate_kind(sidx(15360, [84480] * 20, version=1), 60) == ('whole', '')


@pytest.mark.parametrize('index, fps, reason', [
    (sidx(60000, [1001000, 2002000]), 60, 'both rates fit'),  # whole numbers of both frame lengths
    (sidx(60000, [1500]), 60, 'neither rate fits'),
    (index_fixture('sidx-23.976fps.bin'), 60, 'neither rate fits'),  # YouTube's fps doesn't match the index
    (b'', 24, 'no index'),
    (b'\x00\x00\x02\xb4moof' + bytes(40), 24, 'no index'),
    (index_fixture('sidx-60fps.bin')[:30], 60, 'short index'),
    (sidx(15360, []), 60, 'empty index'),
    (sidx(0, [256]), 60, 'empty index'),
    (index_fixture('sidx-60fps.bin'), 0, 'no fps'),
])
def test_rate_kind_unknown(index, fps, reason):
    assert mpd.rate_kind(index, fps) == (None, reason)


def test_index_candidates_are_mp4_video_smallest_first():
    small = fmt(394, 'video/mp4; codecs="av01.0.00M.08"', 144, bitrate=80000,
                indexRange={'start': '700', 'end': '5000'})
    tiny = fmt(160, 'video/mp4; codecs="avc1.4D400C"', 144, bitrate=60000,
               indexRange={'start': '741', 'end': '900'})
    candidates = mpd.index_candidates(FORMATS + [small, tiny])
    assert [(f['itag'], byte_range) for f, byte_range in candidates[:2]] == [(160, '741-900'), (394, '700-1099')]
    assert {mpd._mime_codec(f)[0] for f, _ in candidates} == {'video/mp4'}  # no WebM, no audio


@pytest.mark.parametrize('rate, expected', [
    ('ntsc', {'136': '24000/1001', '137': '25000/1001', '298': '30000/1001', '299': '60000/1001',
              '303': '50000/1001'}),
    ('whole', {'136': '24', '137': '25', '298': '30', '299': '60', '303': '50'}),
    (None, {'136': '24', '137': '25', '298': '30', '299': '60', '303': '50'}),
])
def test_frame_rates_follow_the_index(rate, expected):
    """YouTube gives 23.976, 29.97 and 59.94 fps as 24, 30 and 60: only the index says which they are."""
    videos = [fmt(itag, 'video/mp4; codecs="avc1.640028"', 1080, fps=fps)
              for itag, fps in ((136, 24), (137, 25), (298, 30), (299, 60), (303, 50))]
    player = {'streamingData': {'adaptiveFormats': videos + FORMATS[-1:]}}
    root = ET.fromstring(mpd.build(player, rate=rate))
    rates = {r.get('id'): r.get('frameRate') for r in root.iter('{%s}Representation' % NS['d'])}
    assert {itag: rates[itag] for itag in expected} == expected


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


def test_qualities_list_each_codec_best_first():
    assert mpd.qualities(FORMATS) == [(2160, 30, True, 'vp9'), (2160, 30, False, 'vp9'),
                                      (1080, 30, False, 'av01'), (1080, 30, False, 'vp9'), (1080, 30, False, 'avc1')]
    assert (2160, 30, True, 'vp9') not in mpd.qualities(FORMATS, allow_hdr=False)


def test_qualities_put_the_preferred_codec_first():
    assert [q[3] for q in mpd.qualities(FORMATS, codec='avc1') if q[0] == 1080] == ['avc1', 'av01', 'vp9']


def test_quality_of_a_vertical_video_is_its_short_side():
    fmt = {'width': 1080, 'height': 1920, 'fps': 30, 'mimeType': 'video/mp4; codecs="avc1.640028"'}
    assert mpd.quality_of(fmt) == (1080, 30, False, 'avc1')


def test_build_for_one_quality_offers_only_it():
    resp = {'streamingData': {'adaptiveFormats': FORMATS}, 'videoDetails': {'lengthSeconds': '60'}}
    root = ET.fromstring(mpd.build(resp, quality=(1080, 30, False, 'vp9')))
    videos = [r for r in root.iter('{%s}Representation' % NS['d']) if r.get('height')]
    assert [(r.get('id'), r.get('height')) for r in videos] == [('248', '1080')]


def test_bitrate_of_a_quality_prefers_the_average_rate():
    assert mpd.bitrate_of(FORMATS, (1080, 30, False, 'avc1')) == 137000
    averaged = [dict(FORMATS[0], averageBitrate=90000)] + FORMATS[1:]
    assert mpd.bitrate_of(averaged, (1080, 30, False, 'avc1')) == 90000
    assert mpd.bitrate_of(FORMATS, (480, 30, False, 'avc1')) == 0
