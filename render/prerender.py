
def find_all(s, exp):
    index = 0
    while True:
        index = s.find(exp, index)
        if index == -1:
            break
        yield index
        index += len(exp)

class PreRenderer:
    def __init__(self, extensions):
        pass
        self.extensions = extensions
    
    def render(self, text):
        new_text = []
        end_i = -1
        for start_i in find_all(text, '{|'):
            new_text.append(text[end_i+1:start_i])
            
            end_i = text.find('}', start_i)
            if end_i == -1:
                end_i = start_i - 1
                continue
            next_newline_i = text.find('\n', start_i)
            if next_newline_i != -1 and end_i > next_newline_i:
                end_i = start_i - 1
                continue
            
            command = text[start_i+2:end_i]
            command, arg = command.split(' ', 1)
            #print(command, arg)
            command_res = self.extensions[command](command, arg)
            new_text.append(command_res)
        
        new_text.append(text[end_i+1:])
        
        return "".join(new_text)

def main():
    def replace_ext(command, arg):
        return "REPLACE({})".format(arg)
    r = PreRenderer({'replace': replace_ext})

    s = """{|replace abcs}ff
        abcd aa ss
        {|replace abcd}
        X-{|replace abcd}-X
        {|replace asd
        qwer{x a}
        ee{|replace abce}"""
    res = r.render(s)
    print(res)

if __name__ == "__main__":
    main()