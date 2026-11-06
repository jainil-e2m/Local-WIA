/** Bounded GET-only Calendar feasibility test using existing Google OAuth client.
 * node knowledge_base/wia-knowledge-base/verification/calendar/verify_calendar.mjs [--await-consent]
 */
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {accessToken,calendarScopes,config,storedTokens} from '../google/oauth_store.mjs';
const out=path.dirname(fileURLToPath(import.meta.url));
const report={started_at_utc:new Date().toISOString(),source:'Google Calendar',mode:'GET_only',
 expected_account:'hello@weddingindustryads.com',requested_scopes:calendarScopes,
 limits:{calendar_list_pages:3,calendars_sampled:3,event_pages_per_calendar:2,events_per_page:100},
 calls:[],calendars:[],event_samples:[],event_details:[],notifications_registered:false,
 calendar_or_invitation_modifications:false,full_backfill:false,status:'preflight'};
let bearer;
const shape=v=>v&&typeof v==='object'?Object.keys(v).sort():[];
const save=()=>writeFile(path.join(out,'live_probe.json'),JSON.stringify(report,null,2)+'\n');
async function get(label,endpoint,params={}){
 const url=new URL(`https://www.googleapis.com/calendar/v3${endpoint}`);
 for(const[k,v]of Object.entries(params))url.searchParams.set(k,String(v));
 const c={label,method:'GET',endpoint,requested_at_utc:new Date().toISOString(),query:Object.fromEntries(Object.entries(params).map(([k,v])=>[k,k==='pageToken'?'[cursor]':v]))};
 report.calls.push(c);
 try{
  const r=await fetch(url,{method:'GET',headers:{Authorization:`Bearer ${bearer}`},redirect:'error',signal:AbortSignal.timeout(25000)});
  c.http_status=r.status;c.ok=r.ok;const d=await r.json();c.response_keys=shape(d);
  if(!r.ok){c.error=String(d?.error?.message??'request_failed').replaceAll(bearer,'[REDACTED]');
   c.error_reasons=(d?.error?.errors??[]).map(e=>e.reason);return null;}return d;
 }catch(e){c.ok=false;c.error=e.name;return null;}
}
function event(e){
 return {id:e.id,iCalUID:e.iCalUID??null,summary:e.summary??null,status:e.status??null,
  event_type:e.eventType??null,html_link:e.htmlLink??null,created:e.created??null,updated:e.updated??null,
  organizer:e.organizer??null,creator:e.creator??null,start:e.start??null,end:e.end??null,
  end_time_unspecified:e.endTimeUnspecified??null,recurring_event_id:e.recurringEventId??null,
  original_start_time:e.originalStartTime??null,recurrence:e.recurrence??null,
  attendees:(e.attendees??[]).map(a=>({email:a.email??null,display_name:a.displayName??null,
   self:a.self??false,organizer:a.organizer??false,optional:a.optional??false,response_status:a.responseStatus??null})),
  attendees_omitted:e.attendeesOmitted??false,visibility:e.visibility??null,transparency:e.transparency??null,
  location:e.location??null,hangout_link:e.hangoutLink??null,conference_data:e.conferenceData??null,
  description_characters:e.description?.length??0,description_excerpt:e.description?.slice(0,700)??'',
  attachment_count:e.attachments?.length??0,response_keys:shape(e)};
}
async function main(){
 const c=await config();const deadline=Date.now()+30*60*1000;
 while(true){
  const tokens=await storedTokens();const granted=new Set((tokens?.scope??'').split(' '));
  if(tokens?.client_id===c.clientId&&calendarScopes.every(s=>granted.has(s)))break;
  report.status='waiting_for_calendar_permissions';await save();
  if(!process.argv.includes('--await-consent')||Date.now()>deadline){report.result='calendar_user_consent_required';return;}
  await new Promise(r=>setTimeout(r,5000));
 }
 bearer=await accessToken();report.status='source_tests_running';await save();
 let pageToken;const apiEnableDeadline=Date.now()+15*60*1000;
 for(let page=0;page<report.limits.calendar_list_pages;page++){
  const data=await get(`calendar_list_${page+1}`,'/users/me/calendarList',{maxResults:100,showHidden:true,...(pageToken?{pageToken}:{})});
  if(!data){
   const failure=report.calls.at(-1);
   const disabled=failure.http_status===403&&(failure.error_reasons?.includes('accessNotConfigured')
    ||failure.error?.includes('has not been used in project'));
   if(disabled&&process.argv.includes('--await-api')&&Date.now()<apiEnableDeadline){
    report.status='waiting_for_calendar_api_enablement';await save();
    await new Promise(r=>setTimeout(r,30000));page--;continue;
   }
   report.result=disabled?'calendar_api_disabled':'calendar_list_read_failed';return;
  }
  report.calendars.push(...(data.items??[]).map(c=>({id:c.id,summary:c.summary,primary:c.primary??false,
   timezone:c.timeZone??null,access_role:c.accessRole??null,selected:c.selected??null,
   hidden:c.hidden??false,deleted:c.deleted??false})));
  if(!data.nextPageToken){report.calendar_list_pagination_complete=true;break;}pageToken=data.nextPageToken;
 }
 const primary=report.calendars.find(c=>c.primary);
 report.primary_calendar=primary??null;
 if(!primary){report.result='primary_calendar_not_verified';return;}
 if(primary.id.toLowerCase()!==report.expected_account){report.result='unexpected_primary_calendar_no_events_read';return;}
 const selected=[primary,...report.calendars.filter(c=>!c.primary&&!c.deleted&&c.access_role!=='freeBusyReader'
  &&/Wedding Industry|\bWIA\b|office.?hours|accelerator/i.test(c.summary??'')).slice(0,2)];
 const now=new Date();const timeMin=new Date(now.getTime()-45*86400000).toISOString();
 const timeMax=new Date(now.getTime()+30*86400000).toISOString();report.event_window={timeMin,timeMax};
 for(const cal of selected){
  const sample={calendar_id:cal.id,calendar_name:cal.summary,events:[],pagination_complete:false};let cursor;
  for(let page=0;page<report.limits.event_pages_per_calendar;page++){
   const data=await get(`events_${cal.id}_${page+1}`,`/calendars/${encodeURIComponent(cal.id)}/events`,{
    timeMin,timeMax,maxResults:100,singleEvents:true,showDeleted:true,orderBy:'startTime',...(cursor?{pageToken:cursor}:{})});
   if(!data)break;sample.timezone=data.timeZone??cal.timezone;
   sample.events.push(...(data.items??[]).map(event));
   if(!data.nextPageToken){sample.pagination_complete=true;break;}cursor=data.nextPageToken;
  }
  report.event_samples.push(sample);
 }
 const examples=report.event_samples.flatMap(s=>s.events.map(e=>({calendar_id:s.calendar_id,event:e})))
  .filter(x=>x.event.summary&&x.event.status!=='cancelled');
 const chosen=[];const add=x=>{if(x&&!chosen.some(y=>y.event.id===x.event.id&&y.calendar_id===x.calendar_id))chosen.push(x);};
 add(examples.find(x=>/Dogwood|Ridgefield|Funktastic|Hybrid|office.?hours|strategy|onboarding/i.test(x.event.summary)));
 add(examples.find(x=>x.event.recurring_event_id));for(const x of examples){if(chosen.length>=3)break;add(x);}
 for(const x of chosen){const data=await get(`event_detail_${x.event.id}`,`/calendars/${encodeURIComponent(x.calendar_id)}/events/${encodeURIComponent(x.event.id)}`);
  if(data)report.event_details.push({calendar_id:x.calendar_id,event:event(data)});}
 const recurring=examples.find(x=>x.event.recurring_event_id);
 if(recurring){
  const id=recurring.event.recurring_event_id;
  const master=await get(`recurring_master_${id}`,`/calendars/${encodeURIComponent(recurring.calendar_id)}/events/${encodeURIComponent(id)}`);
  report.recurring_master=master?event(master):null;
 }
 report.result='bounded_calendar_probe_completed';
}
try{await main();}catch(e){report.result='calendar_probe_not_completed';report.error=e.message;}
report.status=report.result;report.finished_at_utc=new Date().toISOString();await save();
console.log(JSON.stringify({result:report.result,calls:report.calls.length,
 statuses:report.calls.reduce((x,c)=>{const k=c.http_status??'network_error';x[k]=(x[k]??0)+1;return x;},{}),
 calendars:report.calendars.length,event_rows:report.event_samples.reduce((n,s)=>n+s.events.length,0),
 report:'knowledge_base/wia-knowledge-base/verification/calendar/live_probe.json'},null,2));
