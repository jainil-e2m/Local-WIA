"""Read-only fingerprint of real SQL rows/catalog and disabled capabilities."""
import argparse
import json
from backend_pipeline.database import check, TABLES
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.store import canonical_hash
from psycopg import sql

parser = argparse.ArgumentParser()
parser.add_argument('phase',choices=['before','after'])
args = parser.parse_args()
settings = StorageSettings.from_env()
assert not settings.synthetic
assert not settings.generation_enabled and not settings.encoding_enabled and not settings.refinement_enabled
repo = ContentRepository(settings)
tables = {}
with repo.connection() as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    catalog = check(conn)
    for table in sorted(TABLES):
        rows = [r['row'] for r in conn.execute(sql.SQL('SELECT row_to_json(t) AS row FROM {} t').format(sql.Identifier(table)))]
        tables[table] = {'count':len(rows),'hash':canonical_hash(sorted(rows,key=canonical_hash))}
result = {'catalog':catalog,'tables':tables,'external_switches':{'generation':False,'encoding':False,'refinement':False}}
path = settings.artifact_root / 'verification' / 'comparison-real-before.json'
path.parent.mkdir(parents=True,exist_ok=True)
if args.phase=='before':
    path.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
else:
    assert result==json.loads(path.read_text(encoding='utf-8')), 'Real SQL rows/catalog or switches changed'
    path.with_name('comparison-real-after.json').write_text(json.dumps({**result,'real_data_unchanged':True},indent=2,default=str),encoding='utf-8')
print(json.dumps({'phase':args.phase,'counts':{k:v['count'] for k,v in tables.items()},'external_calls':0}))
