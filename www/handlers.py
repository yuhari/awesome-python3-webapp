#!/usr/bin/env python3
'''
url handler
'''
__author__ = 'yuhari'

import re, time, json, logging, hashlib, base64, asyncio
from aiohttp import web

from models import User, Comment, Blog, next_id
from config import configs
from webfrm import get, post
from apis import APIError, APIValueError, APIResourceNotFoundError, APIPermissionError, Page

### pack and unpack access-string related to user
COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs['session']['secret']

def user2cookie(user, max_age):
    pass

async def cookie2user(cookie_str):
    
    if not cookie_str:
        return None
    try:
        l = cookie_str.split('-')
        if len(l) != 3:
            return None
        uid, expires, sha1 = l
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invaild sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

### some functions
def get_page_index(page):
    p = 1
    try:
        p = int(page)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

### url actions
@get('/')
async def index(*,page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(*)')
    page = Page(num, page_index)
    
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='create_time desc', limit=(page.offset, page.limit))
    return {
        '__template__' : 'blogs.html' ,
        'page' : page,
        'blogs' : blogs
    }
    
    