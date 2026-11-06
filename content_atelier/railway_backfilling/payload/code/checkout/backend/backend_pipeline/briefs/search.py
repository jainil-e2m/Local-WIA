from ..config import Settings
from ..store import JsonStore,canonical_hash
from ..matching import vector_valid,vector_digest
from .. import retrieval

def cached_search(repo,text,k=20,source_ids=None):
    """Protected interactive inspection never dispatches inference/encoding."""
    models=Settings.from_env()
    space={'model':models.embedding_model,'endpoint':models.embedding_base_url.rstrip('/'),
        'dimensions':1536,'synthetic':repo.settings.synthetic,'purpose':'brief-query-v1'}
    path=f'brief-query-vectors/{canonical_hash({**space,"text":text})}.json'
    store=JsonStore(repo.settings.artifact_root)
    if not store.path(path).is_file(): return {'status':'awaiting_query_encoding','hits':[],'evidence':[]}
    data=store.read_json(path)
    if data.get('contract')!=space or data['input_hash']!=canonical_hash(text) or not vector_valid(data['vector']) or vector_digest(data['vector'])!=data['digest']:
        raise ValueError('Search query cache integrity failed')
    with repo.connection() as conn:
        snapshot=retrieval.archive(conn,models,repo.settings.synthetic)
        if source_ids:
            if len(set(source_ids))!=len(source_ids) or not set(source_ids).issubset(snapshot['sources']): raise ValueError('Unknown or restricted search source')
            chunks=conn.execute('SELECT chunk_id FROM transcript_chunks WHERE transcript_id=ANY(%s)',(source_ids,)).fetchall()
            snapshot={**snapshot,'chunks':{r['chunk_id']:snapshot['chunks'][r['chunk_id']] for r in chunks}}
        hits=retrieval.search(conn,text,data['vector'],snapshot,k)
        evidence=retrieval.expand(conn,hits[:5],snapshot)
    return {'status':'complete','hits':hits,'evidence':[e.model_dump(mode='json') for e in evidence],'confidence':'retrieval ranks are not factual confidence'}
