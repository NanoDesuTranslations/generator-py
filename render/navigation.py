
from yattag import Doc

from ordering import page_sort_key_predicate

def probably_int(value):
    try:
        int(value)
    except (ValueError, TypeError):
        return False
    else:
        return True

def gen_nav(root, page):
    doc, tag, text, line = Doc().ttl()
    
    if root.series.fixed_nav_entries:
        with tag('li'):
            try:
                line('a', 'About', href=root.children['about'].get_fs_path())
            except KeyError:
                line('a', 'About', href='javascript:void(0)')
    
    def add_children(root):
        for child in root.get_nav_children():
            #nav_text = "{} {}".format(path, child.title) if probably_int(path) else child.title
            nav_text = child.get_title()
            if child.children:
                with tag('li', klass='dropdown-submenu'):
                    with tag('a', href='javascript:void(0)'):
                        with tag('span', style="z-index:2;padding:0 3px;"):
                            doc.attr(onclick='window.location = "{}"'.format(child.get_fs_path()))
                            text('•')
                        text(nav_text)
                    
                    with tag('ul', klass='dropdown-menu'):
                        add_children(child)
            else:
                with tag('li'):
                    line('a', nav_text, href=child.get_fs_path())
    
    for child in root.get_nav_children():
        if child.path_part in ('about', 'contact') and child.series.fixed_nav_entries:
            continue
        
        if child.children:
            with tag('li', klass='dropdown'):
                with tag('a'):
                    attr = {
                        'href': '#',
                        'class': 'dropdown-toggle',
                        'data-toggle': 'dropdown',
                        'role': 'button',
                        'aria-haspopup': 'true',
                        'aria-expanded': 'false',
                    }
                    doc.attr(**attr)
                    #line('span', path)
                    line('span', child.get_title())
                    line('span', '', klass='caret')
                with tag('ul', klass='dropdown-menu'):
                    doc.attr(('data-submenu', ''))
                    add_children(child)
        else:
            with tag('li'):
                with tag('a'):
                    doc.attr(href=child.get_fs_path())
                    text(child.get_title())
    
    if root.series.fixed_nav_entries:
        with tag('li'):
            try:
                line('a', 'Contact', href=root.children['contact'].get_fs_path())
            except KeyError:
                line('a', 'Contact', href='javascript:void(0)')
    
    return doc.getvalue()
