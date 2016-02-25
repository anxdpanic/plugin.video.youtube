__author__ = 'bromix'

import unittest

from resources.lib import kodion
from resources.lib.youtube.client import YouTube
from resources.lib.youtube.helper.video_info import VideoInfo


class TestClient(unittest.TestCase):
    TEST_ACCESS_TOKEN = ''

    def test_calc_next_page_token(self):
        """
        client = YouTube(config=YouTube.CONFIGS['youtube-for-kodi-14-old'], items_per_page=50)
        page_token = ''
        for i in range(0, 500):
            json_data = client.get_playlist_items('UUfwx98Wty7LhdlkxL5PZyLA', page_token=page_token)
            page_token = json_data.get('nextPageToken', '')
            if not page_token:
                break

            print '%d\t%s' % (i, page_token)
            pass
        """


        client = YouTube()
        token = client.calculate_next_page_token(2, 1)
        for i in range(2, 50):
            token = client.calculate_next_page_token(i, 50)
            print 'Page=%d token=%s' % (i, token)
            pass

        pass

    def test_my_subscriptions_tv(self):
        client = YouTube(items_per_page=5, access_token_tv=self.TEST_ACCESS_TOKEN)
        json_data_page1 = client.get_my_subscriptions(page_token=None)
        json_data_page2 = client.get_my_subscriptions(page_token=json_data_page1['next_page_token'], offset=json_data_page1['offset'])
        json_data_page3 = client.get_my_subscriptions(page_token=json_data_page2['next_page_token'], offset=json_data_page2['offset'])
        json_data_page4 = client.get_my_subscriptions(page_token=json_data_page3['next_page_token'], offset=json_data_page3['offset'])
        pass

    def test_get_live_events(self):
        client = YouTube()

        json_data = client.get_live_events(event_type='live')
        pass

    def test_get_channel_by_username(self):
        client = YouTube()

        json_data = client.get_channel_by_username(username='HGTVShows')
        pass

    def test_get_channels(self):
        client = YouTube()

        #json_data = client.get_channels('mine')
        #json_data = client.get_channels(['UCDbAn9LEzqONk__uXA6a9jQ', 'UC8i4HhaJSZhm-fu84Bl72TA'])
        json_data = client.get_channels(['UCZBxCJSGxNVsWpHP3R5YThg'])
        pass

    def test_get_playlist_items(self):
        client = YouTube()

        json_data = client.get_playlist_items(playlist_id='UUZBxCJSGxNVsWpHP3R5YThg')
        pass

    def test_false_language_id(self):
        # empty => 'en-US'
        client = YouTube(language='')
        self.assertEquals('en_US', client.get_language())
        self.assertEquals('US', client.get_country())

        # 'en','de' => 'en-US'
        client = YouTube(language='de')
        self.assertEquals('en_US', client.get_language())
        self.assertEquals('US', client.get_country())

        # 'de-DE-UTF8' => 'en-US'
        client = YouTube(language='de-DE-UTF8')
        self.assertEquals('en_US', client.get_language())
        self.assertEquals('US', client.get_country())

        # 'de-DE' => 'de-DE'
        client = YouTube(language='de-DE')
        self.assertEquals('de_DE', client.get_language())
        self.assertEquals('DE', client.get_country())
        pass

    def test_playlist_item_id_of_video_id(self):
        client = YouTube(language='de-DE')
        json_data = client.get_playlist_item_id_of_video_id(playlist_id='PL3tRBEVW0hiBMoF9ihuu-x_aQVXvFYHIH', video_id='KpjgZ8xAeLI')
        pass

    def test_get_supported_regions(self):
        client = YouTube(language='de-DE')
        json_data = client.get_supported_regions()
        pass

    def test_get_supported_languages(self):
        client = YouTube(language='de-DE')
        json_data = client.get_supported_languages()
        pass

    def test_generate_user_code(self):
        client = YouTube(language='de-DE')
        json_data = client.generate_user_code()
        pass

    def test_popular_videos(self):
        client = YouTube(language='de-DE')

        json_data = client.get_popular_videos()
        pass

    def test_video_categories(self):
        client = YouTube(language='de-DE')
        json_data = client.get_video_categories()
        pass

    def test_channel_sections(self):
        client = YouTube(language='en-US')
        json_data = client.get_channel_sections(channel_id='UCEgdi0XIXXZ-qJOFPf4JSKw')
        pass

    def test_video_category(self):
        client = YouTube(language='en-US')

        json_data = client.get_video_category('17')
        pass

    def test_guide_categories(self):
        client = YouTube(language='en-US')
        json_data = client.get_guide_categories()
        pass

    """
    def test_create_playlist(self):
        client = YouTube()

        token, expires = client.authenticate(self.USERNAME, self.PASSWORD)
        client = YouTube(access_token=token)
        json_data = client.create_playlist(title='BLA')
        pass

    def test_activities(self):
        client = YouTube()

        token, expires = client.authenticate(self.USERNAME, self.PASSWORD)
        client = YouTube(access_token=token)
        #json_data = client.get_uploaded_videos_of_subscriptions()
        json_data = client.get_activities(channel_id='home')
        pass

    def test_guide_category(self):
        client = YouTube(language='de-DE')
        token, expires = client.authenticate(self.USERNAME, self.PASSWORD)
        client = YouTube(language='de-DE', access_token=token)

        # Music
        #json_data = client.get_guide_category('GCTXVzaWM')

        # Best of YouTube
        json_data = client.get_guide_category('GCQmVzdCBvZiBZb3VUdWJl')
        pass

    def test_authenticate(self):
        client = YouTube()
        token, expires = client.authenticate(self.USERNAME, self.PASSWORD)
        pass

    def test_playlist_items_id_of_video(self):
        client = YouTube()

        token, expires = client.authenticate(self.USERNAME, self.PASSWORD)
        client = YouTube(access_token=token)

        playlist_item_id = client.get_playlist_item_id_of_video_id(u'WL', '-Zotg42zEEA')
        pass
    """

    def test_get_video_streams_vevo(self):
        client = YouTube()

        context = kodion.Context()

        # ranadom stuff
        streams = client.get_video_streams(context, 'VznAYy5yL2A')
        #streams = client.get_video_streams(context, 'FlvtHMO6XHY')
        #streams = client.get_video_streams(context, 'zyg0WUsY9HI')

        # Exception: Sign in to confirm your age
        #streams = client.get_video_streams(context, 'B3eAMGXFw1o')

        # VEVO
        #streams = client.get_video_streams(context, 'YQHsXMglC9A')
        #streams = client.get_video_streams(context, 'VHrLPs3_1Fs')
        #streams = client.get_video_streams(context, 'a3ir9HC9vYg')

        #streams = client.get_video_streams(context, 'nfWlot6h_JM')
        self.assertGreater(len(streams), 0)

        # VEVO (Restricted)
        #streams = client.get_video_streams(context, 'O-zpOMYRi0w')
        self.assertGreater(len(streams), 0)

        #streams = client.get_video_streams(context, 'NmugSMBh_iI')
        self.assertGreater(len(streams), 0)

        # VEVO Gema
        # blocked (gema)
        #streams = client.get_video_streams(context, 'XbiH6pQI7pU')
        #self.assertGreater(len(streams), 0)

        pass

    def test_get_streams_live_streams(self):
        client = YouTube()

        context = kodion.Context()

        # working with old addon
        streams = client.get_video_streams(context, 'Hrc4rwZ29y4')

        #Live
        # blocked
        #streams = client.get_video_streams(context, 'y1knc30OqKQ')
        #self.assertGreater(len(streams), 0)

        # blocked
        #streams = client.get_video_streams(context, '7UFbGKo21lc')
        #self.assertGreater(len(streams), 0)

        # private
        #streams = client.get_video_streams(context, 'RqbyYOCAFJU')
        #self.assertGreater(len(streams), 0)

        #streams = client.get_video_streams(context, 'P8-yDTXnXAI')
        #self.assertGreater(len(streams), 0)

        #streams = client.get_video_streams(context, 'pvEWZY3Eqsg')
        #self.assertGreater(len(streams), 0)
        pass

    def test_get_video_streams_rtmpe(self):
        client = YouTube()

        context = kodion.Context()
        #streams = client.get_video_streams(context, 'vIi57zhDl78')
        #self.assertGreater(len(streams), 0)

        # #190 - viewster video
        streams = client.get_video_streams(context, 'xq2aaB_Awno')
        self.assertGreater(len(streams), 0)

        streams = client.get_video_streams(context, 'ZCBlKMZLxZA')
        self.assertGreater(len(streams), 0)
        pass

    def test_get_video_streams_restricted(self):
        client = YouTube()

        context = kodion.Context()

        streams = client.get_video_streams(context, 'oRSijEW_cDM')
        self.assertGreater(len(streams), 0)

    def test_extract_meta_info(self):
        client = YouTube()
        context = kodion.Context()

        # some via 'get_video_info'
        video_info = VideoInfo(context)
        video_streams = video_info._method_get_video_info('d5i0ZMMbkZY')
        pass

    def test_get_video_streams_mixed(self):
        client = YouTube()

        context = kodion.Context()

        # some videos
        streams = client.get_video_streams(context, 'Hp0gI8KJw20')
        self.assertGreater(len(streams), 0)

        # Couch Tomato videos won't play
        streams = client.get_video_streams(context, 'xtPPggoKZjU')
        self.assertGreater(len(streams), 0)

        streams = client.get_video_streams(context, 'OSUy2uA6fbw')
        self.assertGreater(len(streams), 0)

        streams = client.get_video_streams(context, 'niBvN80Jqkg')
        self.assertGreater(len(streams), 0)

        # 60fps
        streams = client.get_video_streams(context, '_zPm3SSj6W8')
        self.assertGreater(len(streams), 0)

        # 1080p ?!?
        streams = client.get_video_streams(context, 'qfPUVz_Hpqo')
        self.assertGreater(len(streams), 0)

        # Restricted?
        streams = client.get_video_streams(context, 'U4DbJWA9JEw')
        self.assertGreater(len(streams), 0)
        pass

    def test_get_playlists(self):
        client = YouTube()

        json_data = client.get_playlists_of_channel(channel_id='UCDbAn9LEzqONk__uXA6a9jQ')
        pass

    def test_get_videos(self):
        client = YouTube()

        json_data = client.get_videos(['uhTYbtZH3Nk'])
        pass

    def test_get_related_videos(self):
        client = YouTube()

        json_data = client.get_related_videos(video_id='dbgPETJ-J9E')
        pass

    def test_search(self):
        client = YouTube()

        # json_data = client.search(q='batman')
        # json_data = client.search(q='batman', search_type='channel')
        json_data = client.search(q='batman', search_type='playlist')
        pass

    pass
