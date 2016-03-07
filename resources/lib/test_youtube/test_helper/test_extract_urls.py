#!/usr/bin/env python
# -*- coding: utf-8 -*

__author__ = 'bromix'

from resources.lib.youtube.helper import extract_urls
import unittest


class TestUrlExtract(unittest.TestCase):
    def test_description_1(self):
        description = (
            'You can play the Forza Horizon 2 Presents Fast & Furious Standalone Pack FOR FREE until April 10! http://bit.ly/1GNrS0a\n'
            'Sponsored Content. Special consideration provided by XBOX.\n'
            '\n'
            'Joven, Ian, and Anthony traverse Southern France in the brand new Standalone Pack from Forza Horizon 2 featuring the cars and missions of the Fast & Furious films. Can you beat our times? Send us a screenshot!\n'
            '\n'
            'Subscribe to Smosh Games ►► http://smo.sh/SubscribeSmoshGames\n'
            'Jovenshire gets Lost in Italy ►► http://smo.sh/LostItaly\n'
            '\n'
            'Play with us!\n'
            'Subscribe: http://smo.sh/SubscribeSmoshGames\n'
            'Like us on Facebook: http://facebook.com/SmoshGames\n'
            'Follow us on Twitter: http://twitter.com/SmoshGames\n'
            'Add us to your circles on Google+: http://google.com/+SmoshGames'
        )
        urls = extract_urls(description)
        self.assertEquals(7, len(urls))
        pass

    def test_description_2(self):
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
        urls = extract_urls(description)
        self.assertEquals(13, len(urls))
        pass

    def test_description_3(self):
        description = 'Subscribe to TRAILERS: http://bit.ly/sxaw6h Catch up with the hottest trailers from the past month in our original epic mashup! Subscribe to COMING SOON: http://bit.ly/H2vZUn Check out all the BEST TRAILER MASHUPS: http://bit.ly/JyKssP Best New Movie Trailers - February 2014 HD Music Credits: Empty Thoughts Over A Shallow Ocean - Ryan Hemsworth https://soundcloud.com/ryanhemsworth Sittin In The Park - Burning Bright ft. 1SP & Symatic (http://freemusicarchive.org/music/Burning_Bright_ft_1SP__Symatic/BLM50_RAISE_THE_BLACK_LANTERN/Black_Lantern_Music_-_BLM-50_RAISE_THE_BLACK_LANTERN_-_07_Sittin_In_The_Park) The Returned http://goo.gl/axzVNr Pompeii http://goo.gl/gMjs2g Battle Of The Damned http://goo.gl/SzNOOs 300: Rise Of An Empire http://goo.gl/h0pT0k Dom Hemingway http://goo.gl/mmzDL6 Triptyque http://goo.gl/zWHxSr The Missing Picture http://goo.gl/TyD5Ul Run & Jump http://goo.gl/gF2QRd The Bag Man http://goo.gl/NV1Jmx The Wait http://goo.gl/3RdT5G The Quiet Roar http://goo.gl/uxq0YD The Raid 2 Berandal http://goo.gl/Sf9XV2 Only Lovers Left Alive http://goo.gl/fg1FgL The Legend of Hercules http://goo.gl/TF7csz Better Living Through Chemistry http://goo.gl/yDBy0E Dead Snow Red vs Dead http://goo.gl/rfJ4f4 Robocop http://goo.gl/hVLLMl Mr X http://goo.gl/bcaSUP Maleficent http://goo.gl/RjJ02i The Lego Movie http://goo.gl/syqxkU Swim Little Fish Swim http://goo.gl/MaSVZz Street Society http://goo.gl/T52aQg Jack Ryan Shadow Recruit http://goo.gl/KVxCP4 Snowpiercer http://goo.gl/8X510l Starred Up http://goo.gl/mfgcWw I, Frankenstein http://goo.gl/0IiCV1 Easy Money Hard To Kill http://goo.gl/BrYTmV American Hustle http://goo.gl/1q581W Visitors http://goo.gl/t6VIfG Walk of Shame http://goo.gl/Idfekc Tide Lines http://goo.gl/zFAa5G The Monkey King http://goo.gl/UQTKuu Enemy http://goo.gl/RRjpCO Make Your Move http://goo.gl/lnoa1d The Bag Man http://goo.gl/NV1Jmx Particle Fever http://goo.gl/dJQAAY The Desert Fish http://goo.gl/0kE7CT The Unknown Known http://goo.gl/ZsswPf Stray Dogs http://goo.gl/BI2h3W Rhymes for Young Ghouls http://goo.gl/ux0p5M Our Man In Tehran http://goo.gl/hdUyZh Rio 2 http://goo.gl/8ELaQn Abuse of Weakness http://goo.gl/filvWj After The Dark http://goo.gl/mquNHn All Hail the King http://goo.gl/O0IzmE Summer in February http://goo.gl/2HJe0L The Missing Picture http://goo.gl/TyD5Ul Bad Words http://goo.gl/ILnyAF Tracks http://goo.gl/zWHxSr The Railway Man http://goo.gl/ankLLE The Suspect http://goo.gl/89MaEJ The Amazing Catfish http://goo.gl/UEPOQr The Better Angels http://goo.gl/YqnHU2 The Strange Little Cat http://goo.gl/SkrTgr The Pretty One http://goo.gl/JYZRGC About Last Night http://goo.gl/LjpHUu Silent But Deadly http://goo.gl/X8Ht2F Elaine Stritch Shoot Me http://goo.gl/j19ybM movieclips movie clips movieclipstrailers trailers hd "best new trailers" "new trailers" trailers hd 300 "300 rise of an empire" "the raid 2" "i frankenstein" "american hustle" "dead snow 2" robocop enemy "jake gyllenhaal" maleficent "mr x" "leos carax" "better living through chemistry" "jack ryan" "stray dogs" shellsyo'
        urls = extract_urls(description)
        self.assertEquals(63, len(urls))
        pass

    pass
