import re,html,sys
def txt(f,enc=None):
    b=open(f,'rb').read()
    try: h=b.decode(enc or 'utf-8')
    except Exception: h=b.decode('latin-1')
    t=re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>','',h); t=re.sub(r'(?is)<!--.*?-->','',t)
    t=re.sub(r'(?i)<(br|/p|/tr|/div|/li|/h\d|/td)[^>]*>','\n',t); t=re.sub(r'<[^>]+>',' ',t); t=html.unescape(t).replace('\xa0',' ')
    t=re.sub(r'[ \t\r]+',' ',t); return re.sub(r'\n\s*\n+','\n',t)
if __name__=='__main__':
    t=txt(sys.argv[1]); 
    if len(sys.argv)>2:
        for m in re.finditer(sys.argv[2],t): print('...',t[max(0,m.start()-int(sys.argv[3]) if len(sys.argv)>3 else m.start()-200):m.end()+(int(sys.argv[3]) if len(sys.argv)>3 else 200)].replace('\n',' | '))
    else: print(t)
