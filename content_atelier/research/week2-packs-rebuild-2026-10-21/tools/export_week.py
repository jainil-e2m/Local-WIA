import psycopg as psycopg2, json, sys, os, re
conn = psycopg2.connect('host=127.0.0.1 port=25440 user=atelier password=atelier_ci_only dbname=atelier_work')
cur = conn.cursor()
cur.execute("select transcript_id, title, call_type, included, source_metadata, original_text from transcripts where week_id=%s order by (source_metadata->>'file_order')::int", (sys.argv[1],))
out = sys.argv[2]
for tid, title, ct, inc, meta, text in cur.fetchall():
    fo = meta.get('file_order')
    fn = os.path.join(out, f"T{int(fo):02d}_{ct}_{re.sub(r'[^A-Za-z0-9]+','_',title)[:50]}.txt")
    open(fn, 'w', encoding='utf-8').write(f"# {tid} | {title} | call_type={ct} | included={inc}\n\n" + text)
    print(fn, len(text))
