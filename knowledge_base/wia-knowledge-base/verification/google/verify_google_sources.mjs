/** Bounded, GET-only Gmail/Drive source feasibility checks after user consent.
 * OAuth refresh may POST only to Google's token endpoint. No watch is registered.
 * node knowledge_base/wia-knowledge-base/verification/google/verify_google_sources.mjs [--gmail|--drive]
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { accessToken, config, directory, root, storedTokens } from './oauth_store.mjs';
let bearer;
const shape = v => v && typeof v === 'object' ? Object.keys(v).sort() : [];
const safe = v => typeof v === 'string' && bearer ? v.replaceAll(bearer, '[REDACTED]') : v;
async function get(report, label, rawUrl, params = {}, asText = false) {
  const url = new URL(rawUrl);
  if (!['gmail.googleapis.com','www.googleapis.com','docs.googleapis.com','sheets.googleapis.com'].includes(url.hostname)) {
    throw new Error('unexpected_api_host');
  }
  for (const [k,v] of Object.entries(params)) url.searchParams.set(k,String(v));
  const call = { label, method: 'GET', endpoint: rawUrl,
    query: Object.fromEntries(Object.entries(params).map(([k,v]) => [k, /pageToken/.test(k) ? '[cursor]' : v])) };
  report.calls.push(call);
  try {
    const res = await fetch(url, { method:'GET', headers:{ Authorization:`Bearer ${bearer}`, Accept:asText?'text/plain':'application/json' },
      redirect:'error', signal:AbortSignal.timeout(25000) });
    call.http_status=res.status; call.ok=res.ok;
    const text=await res.text(); let data; try { data=JSON.parse(text); } catch { data=null; }
    if (!res.ok) { call.error=safe(JSON.stringify(data?.error?.message ?? text.slice(0,160)));
      call.error_status=data?.error?.status ?? null; return null; }
    if (asText) { call.characters=text.length; return text; }
    call.response_keys=shape(data); return data;
  } catch(e) { call.ok=false; call.error=e.name; call.cause_code=e.cause?.code ?? null; return null; }
}
const makeReport = name => ({ source:name, review_date:'2026-10-19', started_at_utc:new Date().toISOString(),
  mode:'bounded_GET_only_source_reads', calls:[], full_backfill:false,
  notifications_registered:false, content_modifications:false });
async function save(report, directory) {
  report.finished_at_utc=new Date().toISOString();
  const dir=path.join(root, `knowledge_base/wia-knowledge-base/verification/${directory}`); await mkdir(dir,{recursive:true});
  await writeFile(path.join(dir,'live_probe.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({source:report.source,result:report.result,calls:report.calls.length,
    statuses:report.calls.reduce((s,c)=>{const k=c.http_status??'network_error';s[k]=(s[k]??0)+1;return s;},{}),
    mailbox:report.profile?.emailAddress, sample_messages:report.messages?.length,
    drive_user:report.user?.emailAddress, file_metadata:report.files?.length,
    document_samples:report.documents?.length, sheet_samples:report.sheets?.length,
    report:`knowledge_base/wia-knowledge-base/verification/${directory}/live_probe.json`},null,2));
}
const fromBase64 = value => value ? Buffer.from(value,'base64url').toString('utf8') : '';
const stripHtml = text => text.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,' ')
  .replace(/<[^>]+>/g,' ').replace(/&nbsp;/g,' ').replace(/&amp;/g,'&').replace(/\s+/g,' ').trim();
function mailContent(message) {
  const headers=Object.fromEntries((message.payload?.headers??[]).map(h=>[h.name.toLowerCase(),h.value]));
  const parts=[]; const attachments=[];
  function walk(p) {
    if (p.filename) attachments.push({ filename:p.filename,mime_type:p.mimeType,size:p.body?.size??null,
      attachment_id:p.body?.attachmentId??null,part_id:p.partId??null });
    if (['text/plain','text/html'].includes(p.mimeType) && p.body?.data) parts.push({type:p.mimeType,text:fromBase64(p.body.data)});
    for (const child of p.parts??[]) walk(child);
  }
  if(message.payload)walk(message.payload);
  const plain=parts.filter(p=>p.type==='text/plain').map(p=>p.text).join('\n');
  const text=plain||stripHtml(parts.filter(p=>p.type==='text/html').map(p=>p.text).join('\n'));
  const all=parts.map(p=>p.text).join('\n').replaceAll('&amp;','&');
  const urls=[...new Set(all.match(/https?:\/\/[^\s<>"')\]]+/g)??[])];
  return { id:message.id,thread_id:message.threadId,internal_date:message.internalDate??null,
    label_ids:message.labelIds??[],subject:headers.subject??null,from:headers.from??null,to:headers.to??null,
    date:headers.date??null,reply_to:headers['reply-to']??null,message_id_header:headers['message-id']??null,
    in_reply_to:headers['in-reply-to']??null,mime_type:message.payload?.mimeType??null,
    body_characters:text.length,body_excerpt:safe(text.slice(0,1500)),text_part_types:parts.map(p=>p.type),
    url_count:urls.length,url_domains:[...new Set(urls.map(u=>{try{return new URL(u).hostname;}catch{return'invalid';}}))],
    dubsado_url_samples:urls.filter(u=>/\/public\/(?:invoices|contract)|portal\.weddingindustryads\.com/i.test(u))
      .concat(urls.filter(u=>/dubsado/i.test(u))).filter((u,i,a)=>a.indexOf(u)===i).slice(0,3),attachments };
}
async function gmail() {
  const r=makeReport('Gmail');
  r.expected_mailbox='hello@weddingindustryads.com';
  r.profile=await get(r,'mailbox_profile','https://gmail.googleapis.com/gmail/v1/users/me/profile');
  if(!r.profile){r.result='mailbox_profile_failed';await save(r,'gmail');return;}
  if(r.profile.emailAddress?.toLowerCase()!==r.expected_mailbox){
    r.result='authorized_mailbox_differs_from_expected_no_message_bodies_read';await save(r,'gmail');return;
  }
  const labels=await get(r,'mailbox_labels','https://gmail.googleapis.com/gmail/v1/users/me/labels');
  r.labels=(labels?.labels??[]).map(l=>({id:l.id,name:l.name,type:l.type}));
  const categories=[
    {name:'dubsado_sender',q:'from:(dubsado.com)'},
    {name:'dubsado_financial_candidates',q:'dubsado {contract invoice payment signed paid}'},
    {name:'known_client_candidates',q:'{"Dogwood Reserve" "Ridgefield" "Funktastic"}'},
    {name:'support_route_candidates',q:'"support@leadlockpro.com"'}];
  r.searches=[]; const selected=new Map();
  for(const category of categories){
    const data=await get(r,category.name,'https://gmail.googleapis.com/gmail/v1/users/me/messages',{q:category.q,maxResults:5});
    const rows=data?.messages??[];
    r.searches.push({...category,returned_count:rows.length,result_size_estimate:data?.resultSizeEstimate??null,
      additional_page_present:Boolean(data?.nextPageToken),message_ids:rows.map(m=>m.id)});
    for(const m of rows.slice(0,2))if(!selected.has(m.id))selected.set(m.id,m);
  }
  r.messages=[];
  for(const message of [...selected.values()].slice(0,8)){
    const full=await get(r,`message_${message.id}`,`https://gmail.googleapis.com/gmail/v1/users/me/messages/${message.id}`,{format:'full'});
    if(full)r.messages.push(mailContent(full));
  }
  r.threads=[];
  for(const id of [...new Set(r.messages.map(m=>m.thread_id))].slice(0,2)){
    const data=await get(r,`thread_${id}`,`https://gmail.googleapis.com/gmail/v1/users/me/threads/${id}`,{format:'metadata'});
    if(data)r.threads.push({id:data.id,messages_returned:data.messages?.length??0,
      message_ids:(data.messages??[]).map(m=>m.id)});
  }
  const candidate=r.messages.flatMap(m=>m.attachments.map(a=>({...a,message_id:m.id})))
    .find(a=>a.attachment_id&&a.size>0&&a.size<=250000&&/pdf|text/i.test(a.mime_type));
  if(candidate){
    const data=await get(r,'bounded_attachment',`https://gmail.googleapis.com/gmail/v1/users/me/messages/${candidate.message_id}/attachments/${candidate.attachment_id}`);
    r.attachment_read={filename:candidate.filename,mime_type:candidate.mime_type,
      decoded_bytes:data?.data?Buffer.from(data.data,'base64url').length:null,content_interpreted:false};
  }
  const history=await get(r,'current_history_cursor','https://gmail.googleapis.com/gmail/v1/users/me/history',
    {startHistoryId:r.profile.historyId,maxResults:2});
  r.history_read={returned_count:history?.history?.length??null,history_id_present:Boolean(history?.historyId),
    live_change_or_notification_verified:false};
  r.result='bounded_source_probe_completed';await save(r,'gmail');
}
const fileFields='id,name,mimeType,parents,modifiedTime,createdTime,webViewLink,driveId,size,shortcutDetails';
function file(f){return Object.fromEntries(fileFields.split(',').map(k=>[k,f[k]??null]));}
function docsText(data){
  const text=[];
  function visit(v){if(!v||typeof v!=='object')return;
    if(v.textRun?.content)text.push(v.textRun.content);
    for(const [k,x]of Object.entries(v)){if(k==='textRun')continue;
      if(Array.isArray(x))x.forEach(visit);else if(x&&typeof x==='object')visit(x);}
  }visit(data);return text.join('');
}
async function drive(){
  const r=makeReport('Google Drive');r.files=[];r.searches=[];r.documents=[];r.sheets=[];
  const about=await get(r,'drive_identity','https://www.googleapis.com/drive/v3/about',{fields:'user(displayName,emailAddress,permissionId)'});
  r.user=about?.user??null;
  if(!r.user){r.result='drive_identity_failed';await save(r,'drive');return;}
  const audit=JSON.parse(await readFile(path.join(root,'knowledge_base/wia-knowledge-base/verification/clickup/local_audit.json'),'utf8'));
  const sheets=audit.attendance_candidates.flatMap(a=>a.candidate_sheet_urls.map(url=>({space:a.space,url,
    id:url.match(/\/spreadsheets\/d\/([^/]+)/)?.[1]}))).filter(s=>s.id).slice(0,2);
  const requests=[{label:'known_client_names',
    q:"trashed=false and (name contains 'Dogwood' or name contains 'Ridgefield' or name contains 'Funktastic')"}];
  requests.push({label:'wia_root_folder_candidates',q:"trashed=false and mimeType='application/vnd.google-apps.folder' and (name contains 'Wedding Industry' or name contains 'WIA')"});
  for(const query of requests){
    const data=await get(r,query.label,'https://www.googleapis.com/drive/v3/files',{q:query.q,pageSize:30,
      fields:`nextPageToken,incompleteSearch,files(${fileFields})`,supportsAllDrives:true,includeItemsFromAllDrives:true});
    const rows=(data?.files??[]).map(file);r.files.push(...rows);
    r.searches.push({...query,returned_count:rows.length,additional_page_present:Boolean(data?.nextPageToken),
      incomplete_search:data?.incompleteSearch??null});
  }
  const folders=r.files.filter(f=>f.mimeType==='application/vnd.google-apps.folder').slice(0,2);
  r.folder_reads=[];
  for(const folder of folders){
    const data=await get(r,`folder_children_${folder.id}`,'https://www.googleapis.com/drive/v3/files',{
      q:`trashed=false and '${folder.id}' in parents`,pageSize:30,
      fields:`nextPageToken,incompleteSearch,files(${fileFields})`,supportsAllDrives:true,includeItemsFromAllDrives:true});
    const rows=(data?.files??[]).map(file);r.files.push(...rows);
    r.folder_reads.push({folder_id:folder.id,folder_name:folder.name,returned_count:rows.length,
      additional_page_present:Boolean(data?.nextPageToken)});
  }
  for(const candidate of sheets){
    const metadata=await get(r,`attendance_file_${candidate.id}`,`https://www.googleapis.com/drive/v3/files/${candidate.id}`,{
      fields:fileFields,supportsAllDrives:true});
    if(metadata)r.files.push(file(metadata));
    const data=await get(r,`spreadsheet_metadata_${candidate.id}`,`https://sheets.googleapis.com/v4/spreadsheets/${candidate.id}`,{
      fields:'spreadsheetId,spreadsheetUrl,properties(title,timeZone),sheets(properties(sheetId,title,gridProperties))'});
    const result={source_space:candidate.space,spreadsheet_id:candidate.id,metadata_read:Boolean(data),
      title:data?.properties?.title??null,timezone:data?.properties?.timeZone??null,
      tabs:(data?.sheets??[]).map(s=>s.properties),sample_range:null,sample_values:null};
    const title=data?.sheets?.[0]?.properties?.title;
    if(title){
      const range=`'${title.replaceAll("'","''")}'!A1:L12`;
      const values=await get(r,`attendance_cells_${candidate.id}`,`https://sheets.googleapis.com/v4/spreadsheets/${candidate.id}/values/${encodeURIComponent(range)}`);
      result.sample_range=values?.range??range;result.sample_values=values?.values??null;
    }
    r.sheets.push(result);
  }
  const doc=r.files.find(f=>f.mimeType==='application/vnd.google-apps.document');
  if(doc){
    const data=await get(r,`document_content_${doc.id}`,`https://docs.googleapis.com/v1/documents/${doc.id}`,{includeTabsContent:true});
    const text=data?docsText(data):'';
    const exported=await get(r,`document_export_${doc.id}`,`https://www.googleapis.com/drive/v3/files/${doc.id}/export`,{mimeType:'text/plain'},true);
    r.documents.push({id:doc.id,title:data?.title??doc.name,structured_read:data!==null,
      text_characters:text.length,text_excerpt:safe(text.slice(0,1200)),
      text_export_read:exported!==null,export_characters:exported?.length??null,
      export_sha256:typeof exported==='string'?createHash('sha256').update(exported).digest('hex'):null});
  }
  const cursor=await get(r,'changes_start_cursor','https://www.googleapis.com/drive/v3/changes/startPageToken',{supportsAllDrives:true});
  if(cursor?.startPageToken){
    const changes=await get(r,'current_changes','https://www.googleapis.com/drive/v3/changes',{
      pageToken:cursor.startPageToken,pageSize:10,supportsAllDrives:true,includeItemsFromAllDrives:true,
      fields:'nextPageToken,newStartPageToken,changes(fileId,removed,time)'});
    r.changes_read={start_cursor_obtained:true,returned_count:changes?.changes?.length??null,
      new_start_cursor_present:Boolean(changes?.newStartPageToken),notification_delivery_verified:false};
  }
  r.files=[...new Map(r.files.map(f=>[f.id,f])).values()];
  r.result='bounded_source_probe_completed';await save(r,'drive');
}
const waitingMode=process.argv.includes('--await-consent');
const testStatus={started_at_utc:new Date().toISOString(),status:'not_started',source_requests_read_only:true};
const saveTestStatus=()=>writeFile(path.join(directory,'source_test_status.json'),JSON.stringify(testStatus,null,2)+'\n');
try{
  if(waitingMode){
    const c=await config();const deadline=Date.now()+30*60*1000;
    testStatus.status='waiting_for_google_user_consent';await saveTestStatus();
    console.log('Read-only Gmail/Drive probes queued; waiting for Google consent, maximum 30 minutes.');
    while(true){
      const tokens=await storedTokens();
      if(tokens?.client_id===c.clientId&&tokens.access_token)break;
      if(Date.now()>deadline)throw new Error('google_consent_wait_expired');
      await new Promise(resolve=>setTimeout(resolve,5000));
    }
  }
  testStatus.status='source_tests_running';await saveTestStatus();
  bearer=await accessToken();
  const tokens=await storedTokens();
  console.log('Google user token available; granted scope count: '+(tokens.scope??'').split(' ').filter(Boolean).length);
  if(!process.argv.includes('--drive'))await gmail();
  if(!process.argv.includes('--gmail'))await drive();
  testStatus.status='source_reports_written';testStatus.finished_at_utc=new Date().toISOString();await saveTestStatus();
}catch(e){console.log(JSON.stringify({result:'probe_not_completed',error:e.message,
  oauth_error:e.oauthError??null}));testStatus.status='source_tests_not_completed';
  testStatus.error=e.message;await saveTestStatus();process.exitCode=1;}
