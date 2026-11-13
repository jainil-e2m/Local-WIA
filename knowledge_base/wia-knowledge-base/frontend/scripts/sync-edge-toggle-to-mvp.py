"""Copy the sidebar ribbon toggle into the MVP pages (mvp/index.html and mvp/real_index.html).

The source of truth is src/components/SidebarEdgeToggle.tsx + .css. The MVP pages are a hand-edited export that is
ahead of this source, so they can't be rebuilt from it; instead they carry:
  - the component's CSS (comments stripped, minified), plus a rule hiding the bundle's old account-row collapse button;
  - edge-toggle-mvp.html, a plain-JS twin of the component (same markup and Web Animations);
  - a debounce on the perimeter light's ResizeObserver in the bundle (the SidebarOrbit.tsx fix).
Safe to re-run. See mvp/readme_changes.md note 55.
"""
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
kb = os.path.dirname(os.path.dirname(here))

css = open(os.path.join(kb, 'frontend', 'src', 'components', 'SidebarEdgeToggle.css'), encoding='utf-8').read()
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
css = re.sub(r'\s*\n\s*', ' ', css).strip()
css = re.sub(r'\s*([{};,])\s*', r'\1', css)
style = ('<style id="edge-toggle">\n/* WIA: satin ribbon sidebar toggle. Source of truth: frontend/src/components/SidebarEdgeToggle.tsx + .css; '
         'this is its copy for the MVP page (readme_changes note 55). */\n' + css +
         '\n.sidebar-person .collapse-button{display:none!important}\n</style>\n')
js = open(os.path.join(here, 'edge-toggle-mvp.html'), encoding='utf-8').read()

ORB_OLD = 'let v=new ResizeObserver(m);'
ORB_NEW = ('let v=new ResizeObserver((()=>{let T=0,F=!0;return()=>{if(F){F=!1;return}'
           'n.style.opacity=`0`,clearTimeout(T),T=setTimeout(()=>{m(),n.style.opacity=``},160)}})());')

for name in ['real_index.html', 'index.html']:
    path = os.path.join(kb, 'mvp', name)
    s = open(path, encoding='utf-8').read()
    if '<style id="edge-toggle">' in s:
        i = s.index('<style id="edge-toggle">')
        j = s.index('</script>', s.index('<script id="edge-toggle-js">')) + len('</script>')
        if s[j:j + 1] == '\n':
            j += 1
    else:  # fresh export: insert before the first </head>
        i = j = s.index('</head>')
    s = s[:i] + style + js + s[j:]
    if ORB_NEW not in s:
        if s.count(ORB_OLD) != 1:
            raise SystemExit(f'{name}: perimeter-light ResizeObserver not found; patch it by hand (note 55)')
        s = s.replace(ORB_OLD, ORB_NEW)
    open(path, 'w', encoding='utf-8', newline='').write(s)
    print(name, 'toggle blocks:', s.count('id="edge-toggle-js"'), '| orbit debounced:', ORB_NEW in s)
