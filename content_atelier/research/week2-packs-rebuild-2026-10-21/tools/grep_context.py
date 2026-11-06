import psycopg, re, sys
term = sys.argv[1].lower(); since = sys.argv[2]
conn = psycopg.connect('host=127.0.0.1 port=25440 user=atelier password=atelier_ci_only dbname=atelier_work')
rows = conn.execute("select week_id, title, original_text from transcripts where lower(original_text) like %s and week_id > %s order by week_id", ('%'+term+'%', since)).fetchall()
for wk, title, text in rows:
    # compact cues
    cues = re.findall(r'(\d\d:\d\d:\d\d)\.\d+ --> [^\n]+\n(.*?)(?=\n\n|\Z)', text, re.S)
    lines = [f"[{t}] {b.strip().replace(chr(10),' ')}" for t,b in cues] or text.split('\n')
    idx = [i for i,l in enumerate(lines) if term in l.lower()]
    print(f"\n##### {wk} | {title}")
    shown=set()
    for i in idx:
        for j in range(max(0,i-4), min(len(lines), i+7)):
            if j not in shown:
                print(lines[j][:400]); shown.add(j)
        print('   ...')
