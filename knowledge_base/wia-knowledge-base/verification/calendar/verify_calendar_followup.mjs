/** GET-only future-call and additional WIA host-calendar sample. */
import {readFile,writeFile} from 'node:fs/promises';
import {accessToken} from '../google/oauth_store.mjs';
const out=new URL('./',import.meta.url);
const initial=JSON.parse(await readFile(new URL('live_probe.json',out),'utf8'));
if(initial.primary_calendar?.id!=='hello@weddingindustryads.com')throw new Error('unexpected_account');
const bearer=await accessToken();
const report={started_at_utc:new Date().toISOString(),mode:'GET_only',calls:[],event_samples:[],
 notifications_registered:false,calendar_or_invitation_modifications:false,full_backfill:false};
const now=Date.now();
const selected=[initial.primary_calendar,...initial.calendars.filter(c=>
 ['carmen@weddingindustryads.com','jacqueline@weddingindustryads.com'].includes(c.id))];
for(const cal of selected){
 const timeMin=new Date(now-(cal.primary?0:14*86400000)).toISOString();
 const timeMax=new Date(now+30*86400000).toISOString();
 const sample={calendar_id:cal.id,calendar_name:cal.summary,timeMin,timeMax,events:[],pagination_complete:false};
 let cursor;
 for(let page=0;page<2;page++){
  const endpoint=`/calendars/${encodeURIComponent(cal.id)}/events`;
  const query={timeMin,timeMax,maxResults:100,singleEvents:true,showDeleted:true,orderBy:'startTime',...(cursor?{pageToken:cursor}:{})};
  const url=new URL(`https://www.googleapis.com/calendar/v3${endpoint}`);
  for(const [k,v]of Object.entries(query))url.searchParams.set(k,String(v));
  const call={method:'GET',endpoint,requested_at_utc:new Date().toISOString(),query:{...query,...(cursor?{pageToken:'[cursor]'}:{})}};
  report.calls.push(call);
  const res=await fetch(url,{headers:{Authorization:`Bearer ${bearer}`},redirect:'error',signal:AbortSignal.timeout(25000)});
  const data=await res.json();call.http_status=res.status;call.ok=res.ok;
  if(!res.ok){call.error_reasons=(data.error?.errors??[]).map(e=>e.reason);break;}
  sample.timezone=data.timeZone;
  sample.events.push(...(data.items??[]).map(e=>({id:e.id,iCalUID:e.iCalUID??null,summary:e.summary??null,
   status:e.status,event_type:e.eventType,html_link:e.htmlLink,created:e.created,updated:e.updated,
   start:e.start??null,end:e.end??null,organizer:e.organizer??null,creator:e.creator??null,
   recurring_event_id:e.recurringEventId??null,original_start_time:e.originalStartTime??null,
   attendees:(e.attendees??[]).map(a=>({email:a.email??null,display_name:a.displayName??null,
    self:a.self??false,organizer:a.organizer??false,response_status:a.responseStatus??null})),
   visibility:e.visibility??null,transparency:e.transparency??null,attendees_omitted:e.attendeesOmitted??false,
   description_characters:e.description?.length??0,description_excerpt:e.description?.slice(0,700)??'',
   conference_present:Boolean(e.conferenceData||e.hangoutLink),
   conference_type:e.conferenceData?.conferenceSolution?.key?.type??null,
   attachment_count:e.attachments?.length??0,response_keys:Object.keys(e).sort()})));
  if(!data.nextPageToken){sample.pagination_complete=true;break;}cursor=data.nextPageToken;
 }
 report.event_samples.push(sample);
}
report.finished_at_utc=new Date().toISOString();
report.status=report.calls.every(c=>c.ok)?'bounded_calendar_followup_completed':'partial_failure';
await writeFile(new URL('followup_probe.json',out),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,calls:report.calls.length,samples:report.event_samples.map(s=>({calendar:s.calendar_name,events:s.events.length,complete:s.pagination_complete}))},null,2));
