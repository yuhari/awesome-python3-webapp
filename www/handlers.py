#!/usr/bin/env python3
'''
url handler
'''
__author__ = 'yuhari'

import re, time, json, logging, hashlib, base64, asyncio, os, sys
from aiohttp import web
import markdown2

from models import User, Comment, Blog, next_id

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','conf'))
from config import configs
from webfrm import get, post
from apis import APIError, APIValueError, APIResourceNotFoundError, APIPermissionError, Page

### pack and unpack access-string related to user
COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs['session']['secret']

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\.\-\_]+(\.[a-z0-9\.\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

def check_admiin(request):
    if request.__user__ is None or request.__user__.admin:
        raise APIPermissionError()

def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    l = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(l)

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

def text2html(text):
    lines = map(lambda s : '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() !='', text.split('\n')))
    return ''.join(lines)

#### mang url actions
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

@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Commit.findAll('blog_id=?', [id], orderBy='create_time desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__' : 'blog.html',
        'blog' : blog,
        'comments' : comments
    }

@get('/register')
def register():
    return {
        '__template__' : 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__' : 'signin.html'
    }

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

@get('/manage/')
def manage():
    return 'redirect:/manage/comments'

@get('/manage/blogs')
def manage_blogs(*,page='1'):
    return {
        '__template__' : 'manage_blogs.html' ,
        'page_index' : get_page_index(page)
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__' : 'manage_blog_edit.html',
        'id' : '' ,
        'action' : '/api/blogs'
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*,id):
    return {
        '__template__' :'manage_blog_edit.html' ,
        'id' : id,
        'action' : '/api/blogs/%s' % id
    }

@get('/manage/comments')
def manage_comments(*,page='1'):
    return {
        '__template__' : 'manage_comments.html',
        'page_index' : get_page_index(page)
    }

@get('/manage/users')
def manage_user(*,page='1'):
    return {
        '__template__' : 'manage_users.html',
        'page_index' : get_page_index(page)
    }

@get('/api/comments')
async def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = await Commit.findNumber('count(*)')
    p = Page(num, page_index)
    
    if num == 0:
        return dict(page=p, comments=())
    comments = await Comment.findAll(orderBy='create_time desc', limit=(p.offset, p.limit))
    return dict(page=p, comments= comments)

@get('/api/blogs/{id}')
async def api_get_blog(id):
    blog = await Blog.find(id)
    return blog

@get('/api/blogs')
async def api_blogs(*,page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(*)')
    p = Page(num, page_index)
    
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='create_time desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs = blogs)

@get('/api/users')
async def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = await User.findNumber('count(*)')
    p = Page(num, page_index)
    
    if num == 0:
        return dict(page=p, users=())
    users = await User.findAll(orderBy='create_time desc', limit=(p.offset, p.limit))
    return dict(page=p, users= users)

@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    
    users = await User.findAll('email=?',[email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    
    user = users[0]
    # check password
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if (sha1.hexdigest() != user.passwd):
        raise APIValueError('passwd', 'Invalid password.')
    # set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email', 'Invalid email.')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd', 'Invalid password.')
    
    users = await User.findAll('email=?', [email])
    if len(users) > 0 :
        raise APIError('register:failed', 'email','Email is already in use.')
    
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email= email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.cotent_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii= False).encode('utf-8')
    return r

@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    
    blog = Blog(user_id=request.__user__.id, user_name = request.__user__.name, user_image=request.__user__.image,name=name.strip(),summary=summary.strip(),content=content.strip())
    await blog.save()
    return blog

@post('/api/blogs/{id}')
async def api_update_blog(id, request, *,name, summary, content):
    check_admin(request)
    
    blog = await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog

@post('/api/blogs/{id}/delete')
async def api_delete_blog(request, *,id):
    check_admin(request)
    
    blog = await Blog.find(id)
    await blog.delete()
    return dict(id=id)

@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content):
    user = request.__user__
    
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    await comment.save()
    return comment

@post('/api/comments/{id}/delete')
async def api_delete_comments(id, request):
    check_admin(request)
    
    c = await Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    await c.delete()
    return dict(id=id)