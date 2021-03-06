import markdown
import mistune
import pystache

from .navigation import gen_nav
from ordering import page_sort_key_predicate

_default_templates = {
    'page': 'layouts/page.stache',
    'chapter-inner': 'layouts/chapter-inner.stache',
    'disqus': 'layouts/disqus.stache',
    'google-analytics': 'layouts/google-analytics.stache',
    'social-media': 'layouts/socialbs.stache',
}

class PageRenderer:
    def __init__(self, config, *, prerenderer=None):
        self.url_prefix = config.path_prefix
        self.config = config
        self.templates = {}
        self.load_templates()
        self.hard_links = False
        self.navigation = None
        self.prerenderer = prerenderer
        
        renderer = mistune.Renderer(escape=False)
        mistune_markdown = mistune.Markdown(renderer=renderer)
        self._mistune_markdown = mistune_markdown
    
    def load_templates(self):
        for template_name, template_fn in _default_templates.items():
            with open(template_fn, encoding='utf8') as f:
                self.templates[template_name] = f.read()
    
    def render(self, page, template_key, inner_template=None, *, inner_only=False):
        url_prefix = self.url_prefix
        config = self.config
        templates = self.templates
        renderers = page.renderer.split('+') if page.renderer else []
        
        wrap_tag = 'div' if 'markdown' in renderers else 'pre'
        #prefix = "<{} style='font-family:Comic Neue, Helvetica, Hack;max-width:100%;'>".format(wrap_tag)
        prefix = "<{}>".format(wrap_tag)
        
        # def format_link(page):
        #     if not page.is_index:
        #         if page.user_path:
        #             return "<a href=\"{0}\" />{1}</a>".format(page.path_part, page.title)
        #         else:
        #             return "<a href=\"{0}\" />{0}: {1}</a>".format(page.path_part, page.title)
        #     else:
        #         return "<a href=\"{0}\" />{1} {0}</a>".format(page.path_part, page.get_index_title())
        #
        def format_link(page):
            return "<a href=\"{0}\" />{1}</a>".format(page.path_part, page.get_title())
        
        if self.hard_links:
            prefix += "<br>".join(format_link(child) for child in page)
            
            if not renderers:
                prefix += '\n\n'
            else:
                prefix += '<br><br>'
        
        postfix = "</{}>".format(wrap_tag)
        
        if 'precode' in renderers:
            prefix += '<code><pre style="white-space: pre-wrap;word-wrap: break-word;">'
            postfix = '</pre></code>' + postfix
        
        if not page.is_index:
            content = page.content
            if 'preproc' in renderers:
                if self.prerenderer is not None:
                    content = self.prerenderer.render(content)
            if 'markdown' in renderers or 'markdown-mistune' in renderers:
                content = self._mistune_markdown(content)
            if 'markdown-mistune-nohtml' in renderers:
                content = mistune.markdown(content)
            if 'markdown-markdown' in renderers:
                content = markdown.markdown(content, extensions=['markdown.extensions.footnotes'])
            content = prefix + content + postfix
            title = page.title
        else:
            content = prefix + postfix
            title = "Index"
        
        if self.navigation is None or page.series.id != self.navigation[0]:
            self.navigation = (page.series.id, gen_nav(page.root, page))
        
        if inner_only:
            return content
        
        params = {
            'content': content,
            'rootPath': url_prefix,
            'parent_path': '..',
            'title': title,
            'header_url': page.series.header_url,
            'series_url': page.get_fs_series_path(),
            'navbar': self.navigation[1],
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
        
        if inner_template:
            params['content'] = pystache.render(templates[inner_template], params)
        
        content = pystache.render(templates[template_key], params)
        return content
