from resources.lib.youtube import hls

MASTER = """#EXTM3U
#EXT-X-INDEPENDENT-SEGMENTS
#EXT-X-MEDIA:URI="https://manifest.googlevideo.com/hls_playlist/itag/233/index.m3u8",TYPE=AUDIO,GROUP-ID="233",DEFAULT=YES,AUTOSELECT=YES
#EXT-X-STREAM-INF:BANDWIDTH=290000,CODECS="mp4a.40.5,avc1.42c00b",RESOLUTION=256x144,FRAME-RATE=30
https://manifest.googlevideo.com/hls_playlist/itag/91/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=4500000,CODECS="mp4a.40.2,avc1.4d4020",RESOLUTION=1280x720,FRAME-RATE=60
/hls_playlist/itag/300/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3000000,CODECS="mp4a.40.2,avc1.4d401f",RESOLUTION=1280x720,FRAME-RATE=60
/hls_playlist/itag/298/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=6800000,CODECS="mp4a.40.2,avc1.640028",RESOLUTION=1920x1080,FRAME-RATE=30
itag/301/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=130000,CODECS="mp4a.40.5"
audio/index.m3u8
"""
BASE = 'https://manifest.googlevideo.com/api/manifest/hls_variant/id/x/file/index.m3u8'


def test_variants_best_first_one_per_quality():
    assert hls.variants(MASTER, BASE) == [
        (1080, 30, 'https://manifest.googlevideo.com/api/manifest/hls_variant/id/x/file/itag/301/index.m3u8', 6800000),
        (720, 60, 'https://manifest.googlevideo.com/hls_playlist/itag/300/index.m3u8', 4500000),  # the higher bandwidth
        (144, 30, 'https://manifest.googlevideo.com/hls_playlist/itag/91/index.m3u8', 290000),
    ]


def test_variants_of_a_playlist_without_any():
    assert hls.variants('#EXTM3U\n', BASE) == []


def test_keep_variant_keeps_the_audio_and_only_that_variant():
    kept = hls.keep_variant(MASTER, BASE, 'https://manifest.googlevideo.com/hls_playlist/itag/300/index.m3u8')
    lines = kept.splitlines()
    assert lines[:3] == MASTER.splitlines()[:3]  # header and the audio rendition
    assert [line for line in lines if line.startswith('#EXT-X-STREAM-INF')] == [
        '#EXT-X-STREAM-INF:BANDWIDTH=4500000,CODECS="mp4a.40.2,avc1.4d4020",RESOLUTION=1280x720,FRAME-RATE=60']
    assert lines[-1] == 'https://manifest.googlevideo.com/hls_playlist/itag/300/index.m3u8'


def test_keep_variant_makes_its_uri_absolute():
    kept = hls.keep_variant(MASTER, BASE, hls.variants(MASTER, BASE)[0][2])
    assert kept.splitlines()[-1] == 'https://manifest.googlevideo.com/api/manifest/hls_variant/id/x/file/itag/301/index.m3u8'


def test_variants_prefer_the_average_bandwidth():
    playlist = '\n'.join(['#EXTM3U',
                          '#EXT-X-STREAM-INF:BANDWIDTH=3000000,AVERAGE-BANDWIDTH=1800000,RESOLUTION=1280x720',
                          'https://example.com/720.m3u8'])
    assert hls.variants(playlist, BASE) == [(720, 0, 'https://example.com/720.m3u8', 1800000)]
