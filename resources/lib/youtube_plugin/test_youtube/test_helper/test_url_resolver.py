#!/usr/bin/env python
# -*- coding: utf-8 -*
import time
from ... import kodion

__author__ = 'bromix'

from ...youtube.helper import extract_urls, UrlResolver

import unittest


class TestUrlExtract(unittest.TestCase):
    def test_resolve_urls(self):
        context = kodion.Context()
        resolver = UrlResolver(context)
        resolver.clear()

        # lefloid
        url = 'http://www.youtube.com/lefloid'
        resolved_url = resolver.resolve(url)
        self.assertEquals('https://www.youtube.com/channel/UCLm6s42r_wCbBX0QqXNCTwg', resolved_url)

        # nerdist
        url = 'http://nerdi.st/subscribe'
        resolved_url = resolver.resolve(url)
        self.assertEquals('https://www.youtube.com/channel/UCTAgbu2l6_rBKdbTvEodEDw', resolved_url)
        pass

    def test_urls(self):
        urls = [
            ('https://youtu.be/GdhfwW5zHEY', 'https://www.youtube.com/watch?v=GdhfwW5zHEY&feature=youtu.be'),
            ('https://www.youtube.com/redirect?q=http%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D9DKZbZyW2-g%26list%3DPL3tRBEVW0hiAOf_drlpS1hqZjJknW88cB%26index%3D1&redir_token=IBH7ovJdGv031f2JRlnYAKfq0m98MTQyODE1NjI2MEAxNDI4MDY5ODYw', 'http://www.youtube.com/watch?v=9DKZbZyW2-g&list=PL3tRBEVW0hiAOf_drlpS1hqZjJknW88cB&index=1'),
            ('http://smo.sh/SubscribeSmoshGames', 'https://www.youtube.com/channel/UCJ2ZDzMRgSrxmwphstrm8Ww?sub_confirmation=1'),
            ('http://ow.ly/LcFu4', 'http://www.heise.de/'),
            ('http://goo.gl/CRiy4L', 'http://www.shortnews.de')
        ]

        context = kodion.Context()
        resolver = UrlResolver(context)
        resolver.clear()
        for url in urls:
            resolved_url = resolver.resolve(url[0])
            self.assertEquals(resolved_url, url[1])
            pass
        pass

    def test_resolve_urls_1(self):
        description = 'Subscribe to TRAILERS: http://bit.ly/sxaw6h Catch up with the hottest trailers from the past month in our original epic mashup! Subscribe to COMING SOON: http://bit.ly/H2vZUn Check out all the BEST TRAILER MASHUPS: http://bit.ly/JyKssP Best New Movie Trailers - February 2014 HD Music Credits: Empty Thoughts Over A Shallow Ocean - Ryan Hemsworth https://soundcloud.com/ryanhemsworth Sittin In The Park - Burning Bright ft. 1SP & Symatic (http://freemusicarchive.org/music/Burning_Bright_ft_1SP__Symatic/BLM50_RAISE_THE_BLACK_LANTERN/Black_Lantern_Music_-_BLM-50_RAISE_THE_BLACK_LANTERN_-_07_Sittin_In_The_Park) The Returned http://goo.gl/axzVNr Pompeii http://goo.gl/gMjs2g Battle Of The Damned http://goo.gl/SzNOOs 300: Rise Of An Empire http://goo.gl/h0pT0k Dom Hemingway http://goo.gl/mmzDL6 Triptyque http://goo.gl/zWHxSr The Missing Picture http://goo.gl/TyD5Ul Run & Jump http://goo.gl/gF2QRd The Bag Man http://goo.gl/NV1Jmx The Wait http://goo.gl/3RdT5G The Quiet Roar http://goo.gl/uxq0YD The Raid 2 Berandal http://goo.gl/Sf9XV2 Only Lovers Left Alive http://goo.gl/fg1FgL The Legend of Hercules http://goo.gl/TF7csz Better Living Through Chemistry http://goo.gl/yDBy0E Dead Snow Red vs Dead http://goo.gl/rfJ4f4 Robocop http://goo.gl/hVLLMl Mr X http://goo.gl/bcaSUP Maleficent http://goo.gl/RjJ02i The Lego Movie http://goo.gl/syqxkU Swim Little Fish Swim http://goo.gl/MaSVZz Street Society http://goo.gl/T52aQg Jack Ryan Shadow Recruit http://goo.gl/KVxCP4 Snowpiercer http://goo.gl/8X510l Starred Up http://goo.gl/mfgcWw I, Frankenstein http://goo.gl/0IiCV1 Easy Money Hard To Kill http://goo.gl/BrYTmV American Hustle http://goo.gl/1q581W Visitors http://goo.gl/t6VIfG Walk of Shame http://goo.gl/Idfekc Tide Lines http://goo.gl/zFAa5G The Monkey King http://goo.gl/UQTKuu Enemy http://goo.gl/RRjpCO Make Your Move http://goo.gl/lnoa1d The Bag Man http://goo.gl/NV1Jmx Particle Fever http://goo.gl/dJQAAY The Desert Fish http://goo.gl/0kE7CT The Unknown Known http://goo.gl/ZsswPf Stray Dogs http://goo.gl/BI2h3W Rhymes for Young Ghouls http://goo.gl/ux0p5M Our Man In Tehran http://goo.gl/hdUyZh Rio 2 http://goo.gl/8ELaQn Abuse of Weakness http://goo.gl/filvWj After The Dark http://goo.gl/mquNHn All Hail the King http://goo.gl/O0IzmE Summer in February http://goo.gl/2HJe0L The Missing Picture http://goo.gl/TyD5Ul Bad Words http://goo.gl/ILnyAF Tracks http://goo.gl/zWHxSr The Railway Man http://goo.gl/ankLLE The Suspect http://goo.gl/89MaEJ The Amazing Catfish http://goo.gl/UEPOQr The Better Angels http://goo.gl/YqnHU2 The Strange Little Cat http://goo.gl/SkrTgr The Pretty One http://goo.gl/JYZRGC About Last Night http://goo.gl/LjpHUu Silent But Deadly http://goo.gl/X8Ht2F Elaine Stritch Shoot Me http://goo.gl/j19ybM movieclips movie clips movieclipstrailers trailers hd "best new trailers" "new trailers" trailers hd 300 "300 rise of an empire" "the raid 2" "i frankenstein" "american hustle" "dead snow 2" robocop enemy "jake gyllenhaal" maleficent "mr x" "leos carax" "better living through chemistry" "jack ryan" "stray dogs" shellsyo'

        res_urls = []
        urls = extract_urls(description)
        context = kodion.Context()
        resolver = UrlResolver(context)
        resolver.clear()
        start = time.clock()
        for url in urls:
            res_urls.append(resolver.resolve(url))
            pass
        end = time.clock()
        print end-start
        pass

    def test_resolve_urls_2(self):
        description = (
            'An wild and bizarre adventure through the unreal and the unforgiving... HURRAY!!\n'
            'MORE Scary Games ► https://www.youtube.com/playlist?list=PL3tRBEVW0hiBSFOFhTC5wt75P2BES0rAo\n'
            'Exmortis ► https://youtu.be/GdhfwW5zHEY\n'
            'The House ► https://youtu.be/eQxgWut4T4c\n'
            'Subscribe Today! ► http://bit.ly/Markiplier\n'
            '\n'
            'Play the Game ► http://www.newgrounds.com/portal/view/654784\n'
            '\n'
            'You Might Also Like ▼\n'
            'Markiplier Highlights - https://www.youtube.com/redirect?q=http%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D9DKZbZyW2-g%26list%3DPL3tRBEVW0hiAOf_drlpS1hqZjJknW88cB%26index%3D1&redir_token=IBH7ovJdGv031f2JRlnYAKfq0m98MTQyODE1NjI2MEAxNDI4MDY5ODYw\n'
            'Horror Compilations - https://www.youtube.com/redirect?q=http%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dp03A7QTBuhg%26list%3DPL58D8AC6A97A69F45%26index%3D1&redir_token=IBH7ovJdGv031f2JRlnYAKfq0m98MTQyODE1NjI2MEAxNDI4MDY5ODYw\n'
            'Happy Wheels - https://www.youtube.com/redirect?q=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DveIB_RI8yMY%26list%3DPL3tRBEVW0hiBMoF9ihuu-x_aQVXvFYHIH%26index%3D2&redir_token=IBH7ovJdGv031f2JRlnYAKfq0m98MTQyODE1NjI2MEAxNDI4MDY5ODYw'
            '\n'
            'Follow my Instagram ► http://instagram.com/markipliergram\n'
            'Follow me on Twitter ► https://twitter.com/markiplier\n'
            'Like me on Facebook ► https://www.facebook.com/markiplier\n'
            '\n'
            'T-Shirts ► http://1shirt.com/collections/markiplier/products/markiplier-warfstache\''
            'Livestreams ► http://www.twitch.tv/markiplier'
        )

        res_urls = []
        urls = extract_urls(description)
        context = kodion.Context()
        resolver = UrlResolver(context)
        for url in urls:
            res_urls.append(resolver.resolve(url))
            pass
        pass

    def test_resolve_urls_3(self):
        description = '(http://www.youtubAlle FSK16 und 18 Filme findest du auf http://www.netzkino.de und der gratis Netzkino App! Netzkino Android App - https://play.google.com/store/apps/details?id=de.netzkino.android.ics Netzkino iOS App - https://itunes.apple.com/ch/app/netzkino/id560901396?mt=8 .................................................................. KIFFERWAHN Völlig abgedrehte Musical-Komödie mit Kristen Bell von 2005. Mit: Christian Campbell, Neve Campbell | Regie: Andy Fickman FSK: Freigegeben ab 12 Jahren .................................................................. NETZKINO ABONNIEREN: https://www.youtube.com/user/Netzkino?sub_confirmation=1 .................................................................. NETZKINO ANDROID APP herunterladen - https://play.google.com/store/apps/details?id=de.netzkino.android.ics NETZKINO iOS APP herunterladen - https://itunes.apple.com/ch/app/netzkino/id560901396?mt=8 NETZKINO WINDOWS 8 APP herunterladen - http://apps.microsoft.com/windows/de-de/app/netzkino/fc8ac95f-b14e-44ef-a148-9a4c7bec7919 NETZKINO WINDOWS PHONE APP herunterladen - http://www.windowsphone.com/de-de/store/app/netzkino/3734d2e8-c646-472d-94cb-fc021505867c NETZKINO AMAZON APP herunterladen - http://www.amazon.de/Netzkino-Services-GmbH/dp/B00MR1YQM8 FACEBOOK - https://www.facebook.com/netzkino. TWITTER - https://twitter.com/netzkino GOOGLE+ - https://plus.google.com/+netzkino NETZKINO.DE - http://www.netzkino.de .................................................................. INHALTSANGABE: Jimmy und Mary, das amerikanische Vorzeige-Teenagerpaar schlechthin, bereiten sich auf eine Englisch-Prüfung an der High-School und ein erfülltes Familienleben vor. Doch Jimmy gerät in die Fänge des Marihuana-Dealers und Jazz-Freaks Jack. Ein Zug an der Haschischzigarette und der saubere Jimmy verwandelt sich in ein unmoralisches Monster, das nur noch auf Sex, Anarchie und dem nächsten Joint lechtzt. Widerwärtige Ausschweifungen, Tote, Irrsinn und schwerste Rechtsverletzungen sind die Folge des Stoffes, der Amerika zu vernichten droht. Jimmy und seine neuen Freunde stellen im Drogenrausch die furchtbarsten Dinge an, ständig begleitet von infernalischer Musik. Das schonungslose Ende naht, als die sonst so brave Mary im Rausch des Giftes ihre Qualitäten als Domina entdeckt. COPYRIGHT: Die Lizenz zur Veröffentlichung des Filmes auf Youtube wurde erworben von: Koch Media GmbH. .................................................................. LUST AUF MEHR FILME? Paradise Trouble: http://bit.ly/1m7iawz Neu bei Netzkino: http://bit.ly/PcVRYy HD-Kino: http://bit.ly/1hdR7Ym Actionfilme: http://bit.ly/1fJdA0b Komödien: http://bit.ly/1huGe96 Horrorfilme: http://bit.ly/1huGeWI Thriller: http://bit.ly/1gWMLL3 Alle Playlists: http://bit.ly/1hXRU0z ..................................................................'
        urls = extract_urls(description)
        context = kodion.Context()
        resolver = UrlResolver(context)
        res_urls = []
        for url in urls:
            res_urls.append(resolver.resolve(url))
            pass
        pass
    pass
