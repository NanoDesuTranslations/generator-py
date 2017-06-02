
from pprint import pprint
from datetime import datetime

import markdown
import pystache

from page import Page

class Blog(Page):
    def __init__(self):
        self.posts = []
    
    def add_post(self, post):
        self.posts.append(post)

class BlogPost(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        self.multipost = False
    
    def render(self):
        if self.multipost:
            return self.config.page_renderer.render(self, 'page')
        else:
            return self.config.page_renderer.render(self, 'page', 'chapter-inner')

def process_blog_posts(posts, series):
    blog = Blog()
    
    with open('layouts/blog_post.stache') as f:
        post_template = f.read()
    
    def get_href(post):
        m_blog = post['meta']['blog']
        pub_date = datetime.fromtimestamp(m_blog['published_date']).strftime('%Y-%m-%d')
        href = "{}_{}".format(pub_date, post['meta']['title'].lower().replace(' ', '-'))
        return href
    
    posts = sorted(posts, key=lambda o: o['meta']['blog']['published_date'], reverse=True)
    posts = sorted(posts, key=lambda o: o['meta']['blog']['pinned'], reverse=True)
    
    content = []
    def ca(s):
        content.append(s)
    
    for post in posts:
        m_blog = post['meta']['blog']
        pub_date = datetime.fromtimestamp(m_blog['published_date']).strftime('%Y-%m-%d %H:%M')
        
        href = get_href(post)
        
        preview_content = post['content'].split("\n")
        if len(preview_content) > 10:
            preview_content = preview_content[:10]
            preview_content.append('')
            preview_content.append('<a href="{}">Read More...</a>'.format(href))
        preview_content = "\n".join(preview_content)
        
        preview_content = markdown.markdown(preview_content, extensions=['markdown.extensions.footnotes'])
        
        params = {
            'date': pub_date,
            'pinned': post['meta']['blog']['pinned'],
            'content': preview_content,
            'title': post['meta']['title'],
            'url': href,
        }
        post_html = pystache.render(post_template, params)
        
        ca(post_html)
    
    ca('<div id="disqus_thread" style="min-height: 100px"></div>')
    
    # path = ['blog']
    path = []
    r_page = {
        'content': ''.join(content),
        'meta': {
            'title': 'Blog',
            'hide_nav': True
        },
        #'series': posts[0]['series']
    }
    page = BlogPost(series=series)
    page.set_raw_page(r_page)
    page.multipost = True
    yield path, page
    
    for post in posts:
        href = get_href(post)
        
        post['meta']['hide_nav'] = True
        
        # path = ['blog', href]
        path = [href]
        
        page = BlogPost(series=series)
        page.set_raw_page(post)
        
        yield path, page
