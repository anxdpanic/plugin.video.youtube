#!/usr/bin/env python
# -*- coding: utf-8 -*

__author__ = 'bromix'

from ... import kodion
from ...youtube import Provider
from ...youtube.helper import UrlToItemConverter
from ...youtube.helper import UrlResolver
from ...youtube.helper import extract_urls
import unittest


class TestUrlExtract(unittest.TestCase):
    def test_list_split(self):
        list_63 = []
        for i in range(63):
            list_63.append('Item_%d' % i)
            pass

        list_of_50 = []
        pos = 0
        while pos < len(list_63):
            list_of_50.append(list_63[pos:pos+50])
            pos += 50
            pass

        pass

    def test_complete_sequence(self):
        description = 'Subscribe to TRAILERS: http://bit.ly/sxaw6h Catch up with the hottest trailers from the past month in our original epic mashup! Subscribe to COMING SOON: http://bit.ly/H2vZUn Check out all the BEST TRAILER MASHUPS: http://bit.ly/JyKssP Best New Movie Trailers - February 2014 HD Music Credits: Empty Thoughts Over A Shallow Ocean - Ryan Hemsworth https://soundcloud.com/ryanhemsworth Sittin In The Park - Burning Bright ft. 1SP & Symatic (http://freemusicarchive.org/music/Burning_Bright_ft_1SP__Symatic/BLM50_RAISE_THE_BLACK_LANTERN/Black_Lantern_Music_-_BLM-50_RAISE_THE_BLACK_LANTERN_-_07_Sittin_In_The_Park) The Returned http://goo.gl/axzVNr Pompeii http://goo.gl/gMjs2g Battle Of The Damned http://goo.gl/SzNOOs 300: Rise Of An Empire http://goo.gl/h0pT0k Dom Hemingway http://goo.gl/mmzDL6 Triptyque http://goo.gl/zWHxSr The Missing Picture http://goo.gl/TyD5Ul Run & Jump http://goo.gl/gF2QRd The Bag Man http://goo.gl/NV1Jmx The Wait http://goo.gl/3RdT5G The Quiet Roar http://goo.gl/uxq0YD The Raid 2 Berandal http://goo.gl/Sf9XV2 Only Lovers Left Alive http://goo.gl/fg1FgL The Legend of Hercules http://goo.gl/TF7csz Better Living Through Chemistry http://goo.gl/yDBy0E Dead Snow Red vs Dead http://goo.gl/rfJ4f4 Robocop http://goo.gl/hVLLMl Mr X http://goo.gl/bcaSUP Maleficent http://goo.gl/RjJ02i The Lego Movie http://goo.gl/syqxkU Swim Little Fish Swim http://goo.gl/MaSVZz Street Society http://goo.gl/T52aQg Jack Ryan Shadow Recruit http://goo.gl/KVxCP4 Snowpiercer http://goo.gl/8X510l Starred Up http://goo.gl/mfgcWw I, Frankenstein http://goo.gl/0IiCV1 Easy Money Hard To Kill http://goo.gl/BrYTmV American Hustle http://goo.gl/1q581W Visitors http://goo.gl/t6VIfG Walk of Shame http://goo.gl/Idfekc Tide Lines http://goo.gl/zFAa5G The Monkey King http://goo.gl/UQTKuu Enemy http://goo.gl/RRjpCO Make Your Move http://goo.gl/lnoa1d The Bag Man http://goo.gl/NV1Jmx Particle Fever http://goo.gl/dJQAAY The Desert Fish http://goo.gl/0kE7CT The Unknown Known http://goo.gl/ZsswPf Stray Dogs http://goo.gl/BI2h3W Rhymes for Young Ghouls http://goo.gl/ux0p5M Our Man In Tehran http://goo.gl/hdUyZh Rio 2 http://goo.gl/8ELaQn Abuse of Weakness http://goo.gl/filvWj After The Dark http://goo.gl/mquNHn All Hail the King http://goo.gl/O0IzmE Summer in February http://goo.gl/2HJe0L The Missing Picture http://goo.gl/TyD5Ul Bad Words http://goo.gl/ILnyAF Tracks http://goo.gl/zWHxSr The Railway Man http://goo.gl/ankLLE The Suspect http://goo.gl/89MaEJ The Amazing Catfish http://goo.gl/UEPOQr The Better Angels http://goo.gl/YqnHU2 The Strange Little Cat http://goo.gl/SkrTgr The Pretty One http://goo.gl/JYZRGC About Last Night http://goo.gl/LjpHUu Silent But Deadly http://goo.gl/X8Ht2F Elaine Stritch Shoot Me http://goo.gl/j19ybM movieclips movie clips movieclipstrailers trailers hd "best new trailers" "new trailers" trailers hd 300 "300 rise of an empire" "the raid 2" "i frankenstein" "american hustle" "dead snow 2" robocop enemy "jake gyllenhaal" maleficent "mr x" "leos carax" "better living through chemistry" "jack ryan" "stray dogs" shellsyo'
        urls = extract_urls(description)
        context = kodion.Context()
        resolver = UrlResolver(context)
        res_urls = []
        for url in urls:
            res_urls.append(resolver.resolve(url))
            pass
        pass

        provider = Provider()
        context.set_localization(30502, 'Go to %s')
        url_converter = UrlToItemConverter(flatten=True)
        url_converter.add_urls(res_urls, provider, context)
        items = url_converter.get_items(provider, context)
        pass

    pass
