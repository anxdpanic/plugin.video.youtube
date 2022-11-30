# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""
#from ... import kodion
#from ...youtube.helper import v3
import xbmc
import xbmcaddon
import os
import sqlite3

addonID=xbmcaddon.Addon().getAddonInfo("id")
db_dir = xbmc.translatePath("special://profile/addon_data/"+addonID)
db_path = os.path.join(db_dir, 'tags.db')

db=sqlite3.connect(db_path)

def init():
    #import web_pdb; web_pdb.set_trace()
    with db:
        cur = db.cursor()
        cur.execute("begin")
        cur.execute("create table if not exists tags (tag TEXT, title TEXT, UNIQUE(tag))")
        cur.execute("create table if not exists channels (channel TEXT, title TEXT, uri TEXT, image TEXT, kind TEXT, UNIQUE(channel))")
        cur.execute("create table if not exists channel_tag (channel TEXT, tag TEXT, UNIQUE(channel,tag))")
        db.commit()
        cur.close()
    return
    
def create_channel(channel_id, title, item_uri, image, kind):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("INSERT OR REPLACE INTO channels(channel,title,uri,image,kind) VALUES (?,?,?,?,?);",(channel_id, title, item_uri, image, kind))
    db.commit()
    cur.close()

def create_tag(tag_id, title):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("INSERT OR REPLACE INTO tags(tag,title) VALUES (?,?);",(tag_id, title))
    db.commit()
    cur.close()

def add_channel_tag(channel_id, tag):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("INSERT OR REPLACE INTO channel_tag(tag,channel) VALUES (?,?);",(tag, channel_id))
    db.commit()
    cur.close()

def get_channels(tag):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    if len(tag)>0:
        cur.execute("select channels.channel, channels.title, channels.uri, channels.image from channels join channel_tag on channel_tag.channel = channels.channel where channel_tag.tag = ?;",(tag,))
    else:
        cur.execute("select channels.channel, channels.title, channels.uri, channels.image from channels;")
    rows = cur.fetchall()
    cur.close()
    channels=[]
    for i in range(len(rows)):
        channels.append([rows[i][0],rows[i][1],rows[i][2],rows[i][3]])
    return channels

def get_empty_channels():
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("select channels.channel, channels.title, channels.uri, channels.image from channels left join channel_tag on channel_tag.channel = channels.channel where channel_tag.tag is NULL;")
    rows = cur.fetchall()
    cur.close()
    channels=[]
    for i in range(len(rows)):
        channels.append([rows[i][0],rows[i][1],rows[i][2],rows[i][3]])
    return channels

def get_channel_name(channel_id):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("select title from channels where channel = ?;",(channel_id,))
    row = cur.fetchone()
    cur.close()
    return row[0]

def get_tag_name(tag):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("select title from tags where tag = ?;",(tag,))
    row = cur.fetchone()
    cur.close()
    return row[0]

def get_tags():
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("SELECT DISTINCT tag, title FROM tags;")
    rows = cur.fetchall()
    cur.close()
    tags=[]
    for i in range (len(rows)):
        tags.append([rows[i][0],rows[i][1]])
    return tags

def get_tags_add(channel_id):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("SELECT DISTINCT tags.tag, tags.title FROM tags LEFT JOIN channel_tag on channel_tag.tag = tags.tag and channel_tag.channel = ? WHERE channel_tag.tag is NULL;",(channel_id,))
    rows = cur.fetchall()
    cur.close()
    tags=[]
    for i in range (len(rows)):
        tags.append([rows[i][0],rows[i][1]])
    return tags

def rename_tag(tag_id, new_name):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("UPDATE tags SET title = ? WHERE tag = ?;",(new_name,tag_id))
    db.commit()
    cur.close()

def delete_tag(tag_id):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("DELETE FROM tags WHERE tag = ?;",(tag_id,))
    db.commit()
    cur.execute("DELETE FROM channel_tag WHERE tag = ?;",(tag_id,))
    db.commit()
    cur.close()

def delete_channel_tag(channel_id, tag_id):
    #init()
    cur = db.cursor()
    cur.execute("begin")
    cur.execute("DELETE FROM channel_tag WHERE tag = ? and channel = ?;",(tag_id,channel_id))
    db.commit()
    cur.close()

init()