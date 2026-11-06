from ..config import Settings
from ..store import canonical_hash
from ..artifacts import store_for
from ..matching import vector_valid,vector_digest
from .. import retrieval
from .runtime import query_space

def cached_search(repo,text,k=20,source_ids=None):
    """Protected interactive inspection never dispatches inference/encoding."""
    models=Settings.from_env()
    space=query_space(models,repo.settings.synthetic)
    path=f'brief-query-vectors/{canonical_hash({**space,"text":text})}.json'
    store=store_for(repo.settings)
    if not store.exists(path): return {'status':'awaiting_query_encoding','hits':[],'evidence':[]}
    data=store.read_json(path)
    if data.get('contract')!=space or data['input_hash']!=canonical_hash(text) or not vector_valid(data['vector']) or vector_digest(data['vector'])!=data['digest']:
        raise ValueError('Search query cache integrity failed')
    with repo.connection() as conn:
        snapshot=retrieval.archive(conn,models,repo.settings.synthetic)
        if source_ids:
            if len(set(source_ids))!=len(source_ids) or not set(source_ids).issubset(snapshot['sources']): raise ValueError('Unknown or restricted search source')
            chunks=conn.execute('SELECT chunk_id FROM transcript_chunks WHERE transcript_id=ANY(%s) AND is_current',(source_ids,)).fetchall()
            snapshot={**snapshot,'chunks':{r['chunk_id']:snapshot['chunks'][r['chunk_id']] for r in chunks}}
        hits=retrieval.search(conn,text,data['vector'],snapshot,k)
        evidence=retrieval.expand(conn,hits[:5],snapshot)
    return {'status':'complete','hits':hits,'evidence':[e.model_dump(mode='json') for e in evidence],'confidence':'retrieval ranks are not factual confidence'}
