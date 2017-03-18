from util import try_int

def page_sort_key_predicate(page):
    order = page.order
    order = order or 0
    
    
    order = try_int(order)
    
    path_part_int = try_int(page.path_part)
    
    path_part_str = str(page.path_part)
    
    order_arr = [order, path_part_int, path_part_str]
    return order_arr
