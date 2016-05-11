'''
Created on 17.04.2016

@author: h0d3nt3uf3l
'''
__author__ = 'h0d3nt3uf3l'

from . import yt_login
from random import randint
#import resources.lib.youtube.client.provider
import xbmcaddon
import re

addon = xbmcaddon.Addon()
api_enable = addon.getSetting('youtube.api.enable')
api_key = addon.getSetting('youtube.api.lastused.key')
api_id = addon.getSetting('youtube.api.lastused.id')
api_secret = addon.getSetting('youtube.api.lastused.secret')
aktivated_logins = 5; # Change this value to get the logins above in the rotation 0 - 5 = 6!!

class Change_API():
    CONFIGS = {
        'last_used': {
            'key': '%s' % api_key,
            'id': '%s' % api_id,
            'secret': '%s' % api_secret,
        },
       'login0': { #Youtube Plugin for Kodi #1
            'id': '294899064488-a8kc1k1jd00kamqre0vd2nftuiifrf6a',
            'key': 'AIzaSyCZwQuosFJbQznqnqpqpYlaJWVMn16wBvs',
            'secret': 'KTkBKINN5vf4Owj1NYyXLzbe',
        },
        'login1': { #Youtube Plugin for Kodi #2
            'id': '430572714882-9jp7cc5o2fddgadc6mc8jpukbfb9ls7o',
            'key': 'AIzaSyDB1Te80ITz7XGvWTdsk8U25eTv9YiCKfs',
            'secret': 'zA9wij-flItY35kHpl7sfekx',
        },
        'login2': { #Youtube Plugin for Kodi #3
            'id': '639620369361-boaoj435t2gp4rn3r4qr6nvio29p0frb',
            'key': 'AIzaSyAP4xRmyNJrwWq1p6nJS-VwnrcgHXlYOqk',
            'secret': 'WYndlTAlKiMef8QOcyPCdgWE',
        },
        'login3': { #Youtube Plugin for Kodi #4
            'id': '531513868019-i5hbh08uif89hk3ks6tf8dui9guitueg',
            'key': 'AIzaSyDBAG0tetknUkjZ8ot3Eoy0ImQqX74WYMg',
            'secret': 'TzlgideyMvhBpWbe02Z-1C5r',
        },
        'login4': { #Youtube Plugin for Kodi #5
            'id': '761252151047-sudci23270af36qgip84dv1ic7uvdc8b',
            'key': 'AIzaSyDZ5ey4ORnxjGA25FDBDamyUIjDS-6JEHQ',
            'secret': 'W3ZwJlvJ4SeQhI3kKjlXADY7',
        },
        'login5': { #Youtube Plugin for Kodi #6
            'id': '865191284534-ss09oo0a085spf4uonp3rgfohjshs4e2',
            'key': 'AIzaSyAw6UkcDBiVMxevqhk7XOekPQSwRicJi8Q',
            'secret': 'CR18gzUiMN-WESUtg4tMK5gs',
        },
        'login6': { #Deaktivated / template
            'id': '',
            'key': '',
            'secret': '',
        }
    }
    
    def get_api_key(self, error, last_login, new_logon=False):
        
        if api_enable == 'true':
            return addon.getSetting('youtube.api.key')
        elif error == 'true' or new_logon:
            api_key = self.get_api('key', error, last_login)
        else:
            api_key = addon.getSetting('youtube.api.lastused.key')
        
        return api_key

    def get_api_id(self, error, last_login, new_logon=False):
        
        if api_enable == 'true':
            return addon.getSetting('youtube.api.id')
        elif error == 'true'or new_logon:
            api_id = self.get_api('id', error, last_login)
        else:
            api_id = addon.getSetting('youtube.api.lastused.id')
            
        return api_id

    def get_api_secret(self, error, last_login, new_logon=False):
                
        if api_enable == 'true':
            return addon.getSetting('youtube.api.secret')
        elif error =='true' or new_logon:
            api_secret = self.get_api('secret', error, last_login)
        else:
            api_secret = addon.getSetting('youtube.api.lastused.secret')
        
        return api_secret

    def get_api(self, part, error, last_login):
        
        #last_login = addon.getSetting('youtube.api.lastused.last_login')
        new_login = addon.getSetting('youtube.api.lastused.new_login')
        #error = addon.getSetting('youtube.api.lastused.error')
        if error == 'true':
            if new_login == last_login or new_login == '':
                while new_login == last_login or new_login == '':
                    new_login = login = 'login%i' % randint(0,aktivated_logins)
                addon.setSetting(id='youtube.api.lastused.last_login', value= login)
                addon.setSetting(id='youtube.api.lastused.new_login', value= new_login)
                addon.setSetting(id='youtube.api.lastused.error', value='false')
            else:
                login = new_login
        elif last_login:
            login = last_login
        else:
            login = 'login%i' % randint(0,aktivated_logins)
                    
        addon.setSetting(id='youtube.api.lastused.last_login', value= login)
        
        part_value = self.CONFIGS[login][part]
        
        tempstring = 'youtube.api.lastused.%s' % part
        
        addon.setSetting(id=tempstring, value=part_value)
        
        return part_value
    
    def new_login(self):
        addon.setSetting(id='kodion.access_token', value = '')
        addon.setSetting(id='kodion.refresh_token', value = '')
        addon.setSetting(id='kodion.access_token.expires', value = '')
        addon.setSetting(id='youtube.api.lastused.error', value='false')
        api_error = addon.getSetting('youtube.api.lastused.error')
        addon.setSetting(id='youtube.api.lastused.last_login', value = 'login0')
        api_last_login = addon.getSetting('youtube.api.lastused.last_login')
        
        addon.setSetting(id='youtube.api.lastused.key', value = self.get_api_key(api_error,api_last_login, True))
        addon.setSetting(id='youtube.api.lastused.id', value = self.get_api_id(api_error,api_last_login, True))
        addon.setSetting(id='youtube.api.lastused.secret', value = self.get_api_secret(api_error,api_last_login, True))
        pass