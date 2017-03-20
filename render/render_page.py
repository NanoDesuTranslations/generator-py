import markdown
import pystache

from .navigation import gen_nav
from ordering import page_sort_key_predicate

_default_templates = {
    'chapter': 'layouts/chapter.stache',
    'disqus': 'layouts/disqus.stache',
    'google-analytics': 'layouts/google-analytics.stache',
    'social-media': 'layouts/socialbs.stache',
}

class PageRenderer:
    def __init__(self, config):
        self.url_prefix = config.get('url-prefix', '')
        self.config = config
        self.templates = {}
        self.load_templates()
    
    def load_templates(self):
        for template_name, template_fn in _default_templates.items():
            with open(template_fn) as f:
                self.templates[template_name] = f.read()
    
    def render(self, page):
        url_prefix = self.url_prefix
        config = self.config
        templates = self.templates
        
        wrap_tag = 'div' if page.renderer == 'markdown' else 'pre'
        prefix = "<{} style='font-family:Comic Neue, Helvetica, Hack;max-width:100%;'>".format(wrap_tag)
        
        def format_link(page):
            if not page.is_index:
                if page.user_path:
                    return "<a href=\"{0}\" />{1}</a>".format(page.path_part, page.title)
                else:
                    return "<a href=\"{0}\" />{0}: {1}</a>".format(page.path_part, page.title)
            else:
                return "<a href=\"{0}\" />{1} {0}</a>".format(page.path_part, page.get_index_title())
        
        prefix += "\n<br>".join(format_link(child)for child in page)
        
        if page.renderer is None:
            prefix += '\n\n'
        else:
            prefix += '<br><br>'
        
        postfix = "</{}>".format(wrap_tag)
        
        if page.renderer == 'precode':
            prefix += '<pre><code>'
            postfix = '</pre></code>' + postfix
        
        if not page.is_index:
            content = page.content
            if page.renderer == 'markdown':
                content = markdown.markdown(content, extensions=['markdown.extensions.footnotes'])
            content = prefix + content + postfix
            title = page.title
        else:
            content = prefix + postfix
            title = "Index"
            
        params = {
            'content': content,
            'rootPath': url_prefix,
            'parent_path': '..',
            'title': title,
            'header_url': page.series.header_url,
            'series_url': url_prefix + '/{}'.format(page.series.path_part),
            'navbar': gen_nav(page.root, page),
        }
        
        enabled = config.get('enabled', {})
        if enabled.get('disqus'):
            #always include series prefix for disqus path
            d_path = '/{}/'.format(page.series.path_part)
            d_path += '/'.join(str(p) for p in page.get_path())
            if not d_path.endswith('/'):
                d_path += '/'
            d_path = "http://nanodesutranslations.org" + d_path
            disqus_params = {
                'full_path': d_path
            }
            disqus_html = pystache.render(templates['disqus'], disqus_params)
            params['disqus'] = disqus_html
        
        if enabled.get('google-analytics'):
            params['google_analytics'] = templates['google-analytics']
        
        if enabled.get('social-media'):
            params['social_media'] = templates['social-media']
        
        content = pystache.render(templates['chapter'], params)
        return content