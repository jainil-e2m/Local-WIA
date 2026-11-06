import React from 'react';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {BriefRead,SQLBriefs} from '../components/SQLBriefs';
import type {StoredBriefV1} from '../api/types';
import {renderScreen} from '../testing/render';

test('SQL brief view starts with actual empty storage, without mock packs or auto generation',()=>{
  const html=renderScreen(<SQLBriefs/>,{url:'/studio/briefs?week=week_1',seed:[['/briefs',{query:{week_id:'week_1',limit:50,offset:0}},{items:[],total:0,limit:50,offset:0}]]});
  assert.match(html,/Awaiting approval/);assert.match(html,/Approve an angle to bring its brief here/);
  assert.doesNotMatch(html,/Approve brief|Generate pack/);
});
test('brief reading exposes grounding, prior status, source qualifications and all format jobs',()=>{
  const d={title:'Bounded decision',angle_statement:'Approved argument',audience:'Owners',reader_decision:'Inspect evidence',cta:{text:'Discuss'},reader_promise:'Learn',positioning:null,why_now:'Unknown date',core_insight:'Observation',audience_pain:'Uncertainty',differentiation:'Specific decision',similarity_review:'Incomplete archive',message_spine:['Observe','Qualify','Decide'],narrative:['Explain'],evidence_boundaries:['Not measured'],voice:['Plain'],creative_direction:['Clear'],accessibility:['Captions'],distribution:['Email'],evaluation_signals:['Comprehension'],claims_requiring_consent:[],handoff_checklist:['Review'],claims:[],email:{reader_job:'Explain',direction:'Develop',outline:['Start'],evidence_ids:[]},carousel_reader_job:'Apply',carousel:Array.from({length:8},(_,i)=>({number:i+1,direction:'Bounded step',evidence_ids:[]})),reels:['Recognize','Understand','Choose'].map(reader_job=>({reader_job,direction:'Explain',outline:['Start'],evidence_ids:[]})),prior_differences:{prior:'New mechanism'},open_questions:[],sources:['ev']};
  const row={content_body:{document:d},prior_content_context:[{angle_id:'prior',argument:'Earlier argument',approval_status:'pending',briefs:[],publications:[]}],research_gaps:{items:['Need permission']},selected_evidence:[{evidence_id:'ev',title:'Exact original',role:'anchor',claim_status:'reported',excerpt:'Preserved transcript text',transcript_id:'source',passage_id:'passage',start:0,end:25,qualifications:['Not measured'],public_use:false,attribution_verified:false,source_url:'javascript:alert(1)'}]} as unknown as StoredBriefV1;
  const html=renderToStaticMarkup(<BriefRead brief={row}/>);
  for(const s of ['Not measured','legacy','Earlier argument','New mechanism','Preserved transcript text','Public use unconfirmed','Reel 3','Carousel','Email'])assert.match(html,new RegExp(s,'i'));
  assert.doesNotMatch(html,/javascript:/);
});
