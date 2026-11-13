/** GET-only follow-up: real email threads, bounded attachment, profile/meeting Docs, session-log cells. */
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {accessToken,root} from './oauth_store.mjs';
const token=await accessToken();
const base=path.join(root,'knowledge_base/wia-knowledge-base/verification');
const gmail=JSON.parse(await readFile(path.join(base,'gmail/live_probe.json'),'utf8'));
const drive=JSON.parse(await readFile(path.join(base,'drive/live_probe.json'),'utf8'));
const report={started_at_utc:new Date().toISOString(),mode:'GET_only',calls:[],threads:[],
  documents:[],sheet_sessions:[],attachment:null,source_modifications:false,notifications_registered:false};
async function get(label,rawUrl,params={}){
 const url=new URL(rawUrl);
 if(!['gmail.googleapis.com','docs.googleapis.com','sheets.googleapis.com'].includes(url.hostname))throw new Error('unexpected_api_host');
 for(const[k,v]of Object.entries(params))url.searchParams.set(k,String(v));
 const c={label,method:'GET',endpoint:rawUrl,query:params};report.calls.push(c);
 try{
  const r=await fetch(url,{method:'GET',headers:{Authorization:`Bearer ${token}`},redirect:'error',signal:AbortSignal.timeout(25000)});
  c.http_status=r.status;c.ok=r.ok;const d=await r.json();
  if(!r.ok){c.error=String(d?.error?.message??'request_failed').replaceAll(token,'[REDACTED]');return null;}
  return d;
 }catch(e){c.ok=false;c.error=e.name;return null;}
}
function mail(m){
 const h=Object.fromEntries((m.payload?.headers??[]).map(x=>[x.name.toLowerCase(),x.value]));
 const parts=[],attachments=[];
 function walk(p){if(p.filename)attachments.push({filename:p.filename,type:p.mimeType,size:p.body?.size,
  id:p.body?.attachmentId??null});
  if(p.body?.data&&['text/plain','text/html'].includes(p.mimeType))parts.push({type:p.mimeType,text:Buffer.from(p.body.data,'base64url').toString('utf8')});
  (p.parts??[]).forEach(walk);
 }if(m.payload)walk(m.payload);
 const plain=parts.filter(x=>x.type==='text/plain').map(x=>x.text).join('\n');
 const text=plain||parts.map(x=>x.text).join('\n').replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,' ').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');
 return {id:m.id,thread_id:m.threadId,internal_date:m.internalDate,label_ids:m.labelIds??[],
  subject:h.subject??null,from:h.from??null,to:h.to??null,cc:h.cc??null,bcc:h.bcc??null,
  date:h.date??null,in_reply_to:h['in-reply-to']??null,message_id:h['message-id']??null,
  body_characters:text.length,body_excerpt:text.slice(0,1800),attachments};
}
function documentText(d){let text='';const links=new Set();
 function walk(v){if(!v||typeof v!=='object')return;if(v.textRun?.content)text+=v.textRun.content;
  if(v.textRun?.textStyle?.link?.url)links.add(v.textRun.textStyle.link.url);
  for(const[k,x]of Object.entries(v)){if(k==='textRun')continue;if(Array.isArray(x))x.forEach(walk);else if(x&&typeof x==='object')walk(x);}
 }walk(d);return{text,links:[...links]};
}
async function main(){
 if(gmail.profile.emailAddress!=='hello@weddingindustryads.com')throw new Error('expected_mailbox_not_verified');
 const ids=[...new Set(gmail.messages.filter(m=>m.subject?.includes('Ridgefield')||m.subject?.includes('The Penny')).map(m=>m.thread_id))].slice(0,2);
 for(const id of ids){
  const d=await get(`full_thread_${id}`,`https://gmail.googleapis.com/gmail/v1/users/me/threads/${id}`,{format:'full'});
  if(d)report.threads.push({id:d.id,total_messages:d.messages?.length??0,messages:(d.messages??[]).slice(-12).map(mail),retention_cap:12});
 }
 const found=await get('small_client_pdf_candidate','https://gmail.googleapis.com/gmail/v1/users/me/messages',{
  q:'has:attachment filename:pdf smaller:1M {Ridgefield Funktastic Dogwood}',maxResults:1});
 if(found?.messages?.[0]){
  const id=found.messages[0].id;
  const d=await get(`attachment_message_${id}`,`https://gmail.googleapis.com/gmail/v1/users/me/messages/${id}`,{format:'full'});
  if(d){
   const parsed=mail(d);report.attachment_message=parsed;
   const a=parsed.attachments.find(a=>a.id&&a.type==='application/pdf'&&a.size<=1000000);
   if(a){
    const data=await get('attachment_bytes',`https://gmail.googleapis.com/gmail/v1/users/me/messages/${id}/attachments/${a.id}`);
    const bytes=data?.data?Buffer.from(data.data,'base64url'):null;
    report.attachment={filename:a.filename,type:a.type,decoded_bytes:bytes?.length??null,
     sha256:bytes?createHash('sha256').update(bytes).digest('hex'):null,content_parsed:false,binary_saved:false};
   }
  }
 }
 const candidates=[drive.files.find(f=>f.mimeType==='application/vnd.google-apps.document'&&/Messaging & Positioning Questionnaire/.test(f.name)),
  drive.files.find(f=>f.mimeType==='application/vnd.google-apps.document'&&/Onboarding Questionnaire/.test(f.name)),
  drive.files.find(f=>f.mimeType==='application/vnd.google-apps.document'&&/Ridgefield.*Summary|Summary.*Ridgefield/.test(f.name))].filter(Boolean);
 for(const f of candidates.slice(0,3)){
  const d=await get(`target_document_${f.id}`,`https://docs.googleapis.com/v1/documents/${f.id}`,{includeTabsContent:true});
  if(d){const parsed=documentText(d);report.documents.push({id:f.id,title:d.title,parents:f.parents,
   text_characters:parsed.text.length,text_excerpt:parsed.text.slice(0,6000),links:parsed.links.slice(0,20),
   all_links_count:parsed.links.length,complete_text_retained:parsed.text.length<=6000});}
 }
 for(const s of drive.sheets){
  const tab=s.tabs.find(t=>t.title==='October');if(!tab)continue;
  const range="'October'!A1:L20";
  const d=await get(`attendance_session_rows_${s.spreadsheet_id}`,`https://sheets.googleapis.com/v4/spreadsheets/${s.spreadsheet_id}/values/${encodeURIComponent(range)}`);
  report.sheet_sessions.push({spreadsheet_id:s.spreadsheet_id,title:s.title,tab_id:tab.sheetId,
   range:d?.range??range,values:d?.values??null});
 }
 report.result='followup_completed';
}
try{await main();}catch(e){report.result='followup_incomplete';report.error=e.name;}
report.finished_at_utc=new Date().toISOString();
await writeFile(path.join(base,'google/followup_probe.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({result:report.result,calls:report.calls.length,
 statuses:report.calls.reduce((x,c)=>{const k=c.http_status??'network_error';x[k]=(x[k]??0)+1;return x;},{}),
 thread_sizes:report.threads.map(t=>t.total_messages),document_samples:report.documents.length,
 session_samples:report.sheet_sessions.length,attachment_downloaded:Boolean(report.attachment?.decoded_bytes)},null,2));
