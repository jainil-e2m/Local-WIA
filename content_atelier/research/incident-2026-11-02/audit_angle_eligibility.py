"""Offline editorial audit of the proposed omissions against the exact saved v9 request.

Writes separate review artifacts only; no database access, retries, provider calls or production writes.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
import socket
from collections import Counter

from process_reduced_run import load, OUT, ROOT
from finalize_reduced_selection import REASONS
from backend_pipeline.angle_profiles import (PEOPLE_LABEL, SCENES_LABEL, card_reference_problems,
                                           demote_internal_cards, scene_references)
from backend_pipeline.store import JsonStore
from backend_pipeline.token_budget import preflight

# Judgments describe possibilities, not a prediction that the provider would select an angle.
AUDIT = {
    'S74': ('retain_strong', 'How we prepare a client to understand and approve the campaign before launch.',
            'The agenda includes questionnaire-led preparation, reviewing the previous account, client approval and a follow-up explanation. That can substantiate a WIA standard or client experience, not merely a tutorial.',
            'WARM / Accelerator client experience; belief_ref none is explicitly allowed.',
            'S7 and S80 are retained human/testimonial evidence from this same call, but the omitted scene supplies concrete process detail. One card can combine them; keeping the human line alone is not equivalent.',
            'It is a promised process, not proof the follow-up occurred or produced results; no fresh result is needed to describe the process. The point must be more specific than a standard service agenda.'),
    'S84': ('retain_strong', 'The support continues with a specialist looking at your own account after launch.',
            'Carmen offers individual account reviews, extends the session if necessary and can provide a recorded review when an owner cannot attend. Those details answer what support actually feels like.',
            'WARM / Accelerator differentiation; the KB explicitly lists Office Hours as behind-the-scenes material.',
            'S7 (what the owner wants to learn) and S80 (comparison with previous support) could pair with this scene. Other calls about support do not replace this conversation-specific proof.',
            'Do not publish internal schedules or turn this into Zoom-link instructions. Describe the evidenced support experience without implying unlimited or guaranteed service terms.'),
    'S106': ('weak_but_not_proven_unused', 'A possible closing detail for a client-experience story, not a testimonial.',
             'The team merely says the meeting went well and the client sounded satisfied. It supplies no specific standard, reason or surprising decision and is weak standalone material.',
             'Low standalone fit for the five tests; could be supporting context only.',
             'The retained client statements and substantive recommendations are stronger evidence from the same call. They make this a lower-priority cut, not a logically certain unused scene.',
             'Do not attribute satisfaction to the client or present a team impression as a verified testimonial.'),
    'S129': ('blocked_public', 'No public angle under the current handling rules.',
             'The effective scene and consent are both internal_only. The public-reference validator rejects this reference and the fallback demotes its card.',
             'Internal insights only.',
             'S131 retains a decision about the missing proposal in the same call, also internal-only. This is partial internal-topic coverage, not full replacement.',
             'Omission can reduce internal insight/context. Do not relabel consent or treat anonymisation as permission.'),
    'S138': ('blocked_public', 'No public angle under the current handling rules.',
             'The effective scene and consent are internal_only, regardless of whether an access-handoff story could otherwise show a process.',
             'Internal insights only.',
             'S32 retains a related human line about allowing the owner to provide access later. It does not replace every technical detail.',
             'The restriction is enforced by code, not a judgment that access preparation is inherently uninteresting.'),
    'S144': ('weak_but_not_proven_unused', 'A possible small supporting detail that client feedback was implemented.',
             'The words confirm unspecified changes, but neither the feedback nor the edits are described. They do not independently establish a surprising WIA standard.',
             'Low standalone potential; it is not prohibited public evidence.',
             'Other retained audit scenes supply substantive work, but they cannot establish what these particular changes were.',
             'Never invent the changed page element, an improvement or a resulting conversion lift.'),
    'S158': ('blocked_public', 'No public angle under the current handling rules.',
             'This comes from an internal team meeting, but both consent and sensitivity are internal_only. Team-practice treatment does not override that restriction.',
             'Internal insights only.',
             'The confusing wording is unspecified. The retained private pricing-guide material may supply context, but the restriction is the decisive reason it is not public.',
             'Do not turn private pricing discussion into a public AI-assisted-workflow example.'),
    'S162': ('blocked_public', 'No public angle under the current handling rules.',
             'Effective sensitivity and consent are internal_only; even a WIA-standard reframe cannot cite this scene in a valid public card today.',
             'Internal insights only.',
             'S163 retains a more substantive search-term and match-type assessment from the same account; it is also internal-only.',
             'A tutorial would additionally fail the platform-or-tactic test. That editorial issue is separate from the hard handling restriction.'),
    'S192': ('retain_strong', 'How the inquiry journey informs the copy we write.',
             'Whitney asks for the landing page, pricing guide and follow-up materials, then explains how the interview informs copy and creative. This can prove a system-level WIA approach.',
             'WARM / ELEVATE; belief_ref none can express the method beyond the brief B1-B5.',
             'The retained positioning interview contains strong client language, but this introduction explains how WIA uses it and connects it to the inquiry journey.',
             'A generic positioning-before-ads point risks repeating the September 15 publication. It needs the specific new client process; requested reviews must not be presented as completed.'),
    'S201': ('retain_supporting', 'How we make the next strategic decisions clear to the client.',
             'Budget allocation, channel objectives, keywords and the promised review are explained together. It can support a transparency/process angle although a meeting schedule alone is weak.',
             'WARM / ELEVATE; fit to current waitlist campaign is possible.',
             'It can contextualize S192 and the same call\'s retained human moments. The next-day strategy call exists but is entirely internal-only; it cannot simply substitute as public proof.',
             'No budget result, completed audit or completed next-day discussion can be claimed from this scene.'),
    'S202': ('retain_supporting', 'How we accommodate an owner\'s pace while planning the start.',
             'The no-pressure explanation is a client-experience moment, especially beside Gabe\'s statement about his busy life. It is not a strong standalone differentiator but is permitted evidence.',
             'WARM / Accelerator client experience, subject to current offer terms.',
             'S50 keeps the busy-owner human line. Without the pacing explanation the response WIA gives is less visible.',
             'Do not imply indefinite access, a universal starting rule, or prerequisites to working with WIA.'),
    'S203': ('retain_strong', 'What we help an owner examine beyond the ad account.',
             'The tour connects the owner\'s website work to messaging, landing-page experience, follow-up and support resources. The process can show depth beyond a library of lessons.',
             'WARM / Accelerator behind-the-scenes; the KB explicitly lists Day in the Vault.',
             'S51 retains the owner\'s real website work and S212 the foundational principle, but not all of the specific guided resources and delivery process.',
             'Avoid re-teaching foundations or repeating the recent UVP post. Do not call the Accelerator a course; distinguish current program mechanics from marketing claims.'),
    'S204': ('retain_strong', 'We build the first campaign with your approval, then guide you as you run it.',
             'The scene directly demonstrates the done-for-you launch followed by guided operation, which the strategist must preserve in positioning. No launched-campaign result is necessary to explain that process.',
             'WARM or CONVERT / Google Search Accelerator, currently open.',
             'S51 supplies the owner\'s website context and S206 their preparation question. The original cut removed both detailed explanations.',
             'Do not sell the VIP Day as a standalone offer, imply ongoing management, or convert this owner\'s readiness recommendation into a universal prerequisite.'),
    'S205': ('retain_supporting', 'A supporting detail about how the supported period is explained to an owner.',
             'The clock-start discussion can reinforce the pacing/client-experience story. It is weak as a standalone point but not barred public evidence.',
             'WARM / the relevant Accelerator or bundle; exact terms must come from the offer sheet.',
             'S202 relates to pacing, but it was also proposed for omission. Retaining only S50 would retain the owner\'s situation without this response.',
             'The scene\'s six months must not be generalized to an individual three-month Accelerator. Do not publish gated terms merely because the scene mentions them.'),
    'S206': ('retain_strong', 'You do not need to arrive with your first Google campaign already built.',
             'Gabe compares a previous asset-heavy attempt with what he needs now; Whitney explains that Carmen prepares keywords, copy and headlines for approval. This is a concrete client question answered through WIA\'s delivery model.',
             'WARM or CONVERT / Google Search Accelerator; client_experience or wia_standard.',
             'The preserved human-line label S51 concerns the website. It does not preserve this distinct client question about campaign preparation. Type question does not make the moment less human.',
             'Do not disparage ads as confusing/risky, promise no work for the owner, or portray the program as ongoing campaign management.'),
    'S207': ('retain_supporting', 'Why the plan leaves time to use expert support after launch.',
             'Whitney connects a suggested launch pace with the opportunity to ask real account questions after launch. It can support guided follow-through rather than just a date announcement.',
             'WARM / Accelerator client experience.',
             'S204/S209 explain stages and S84 concerns another client\'s support. Another conversation does not replace Gabe\'s own plan.',
             'Six weeks was a suggested aggressive target, not a promised result, deadline or confirmed client commitment.'),
    'S208': ('retain_strong', 'You know which specialist will review each part of your advertising.',
             'Named people and responsibilities substantiate the KB\'s differentiation that a buyer knows the team, rather than being handed anonymous support.',
             'WARM / Accelerator UVP and team experience.',
             'S210 confirms actual access but does not show the specialist ownership described here. General roster facts are not evidence of what was explained in this call.',
             'Respect identity records and former-staff dates. Avoid a generic staff introduction without the client-facing consequence.'),
    'S209': ('retain_strong', 'What the owner creates and what our team builds and launches on Meta.',
             'Copy/creative feedback, organic-content reuse and WIA\'s launch role make the support model concrete. The strategist\'s positioning rule explicitly requires this division of work.',
             'WARM or CONVERT / Meta Ads Accelerator, currently open.',
             'The four scenes left from Gabe\'s call do not preserve this Meta delivery explanation.',
             'Do not imply WIA makes all the owner\'s creative or performs ongoing management. A general Meta tutorial would fail the five tests.'),
    'S211': ('retain_supporting', 'How access to specialist feedback continues beyond the launch.',
             'Most screen navigation is weak, but access to feedback, replays and recurring expert sessions can support a client-experience point the KB explicitly invites.',
             'WARM / behind-the-scenes and Accelerator support.',
             'S214 is complementary but was also cut. S210 merely confirms access, which is not equivalent to the ongoing-support explanation.',
             'Do not publish internal timetables or imply a new public live event is scheduled; the current plan says to schedule no event without WIA announcing one.'),
    'S213': ('retain_supporting', 'An owner can learn from real questions that other wedding businesses bring.',
             'Gabe asks about participating and describes recognizing another owner\'s problem. It is a client-experience/community moment, not merely a navigation question.',
             'WARM / Accelerator support experience.',
             'S214 gives the support model but was also cut; this scene supplies the owner\'s own reaction, not captured by the retained website-related human line.',
             'No actual peer interaction or benefit has happened yet; do not invent a member success story or call it a large active community.'),
    'S214': ('retain_strong', 'Specific feedback on your own work is part of the guided experience.',
             'Whitney describes the small group, individualized attention, channels for actual ads/landing-page questions and private support. That is concrete service evidence, even if surrounded by UI instructions.',
             'WARM / Accelerator differentiation; behind-the-scenes is explicitly requested.',
             'S50 and S51 keep the client\'s circumstances but not this response. S210 proves access only; S212 teaches a foundation. None substitutes for this individualized-support explanation.',
             'Do not claim unlimited, guaranteed response times or measured member outcomes. Translate insider terms into plain words.'),
    'S282': ('retain_strong', 'How we tailor the follow-up setup around a business\'s workflow.',
             'Whitney explicitly introduces customization and a specialist-led setup. The role of the service, not the fact of a call opening, can be the point.',
             'WARM / LeadLock, or its role in ELEVATE.',
             'The retained S68/S69 concern other client circumstances; S280 concerns Google Ads approval. They do not preserve the LeadLock customization explanation.',
             'The recording ends before the setup is shown. Describe the intended process, not a completed integration or automated-sales result.'),
    'S289': ('retain_strong', 'How the team checks account readiness before a client build session.',
             'Although moment_type is question, evidence_class is team_practice and the actual prompt gives it public process handling. The initial label-based protection missed it.',
             'WARM / behind-the-scenes WIA standard; show practice without client details.',
             'S71 retains excitement about the client but not the access checklist and account-linking follow-up. Other internal-only team scenes cannot serve as public substitutes.',
             'Never quote this internal meeting, name the client, or claim permissions/linking were confirmed. Show only the process the team discusses.'),
}


def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def main():
    socket.socket=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Offline audit forbids network access'))
    snapshot,request,ids,rows,packet,render,ui,suffix,dropped=load()
    assert set(AUDIT)==set(REASONS)
    refs=scene_references(packet)
    inv={mid:ref for ref,mid in refs.items()}
    byid={m['moment_id']:m for m in packet}
    sensitivity={m['moment_id']:m['sensitivity'] for m in packet}
    template=(ROOT/'backend/backend_pipeline/prompt_templates/angle_generation.wia_strategist_v9.md').read_text(encoding='utf-8').strip()
    assert request['messages'][0]['content'].startswith(template+'\n\n')
    audits=[]
    for ref,(verdict,point,reason,fit,coverage,guardrail) in AUDIT.items():
        m=byid[refs[ref]]
        probe={'angles':[{'rank':1,'title':'Local reference eligibility check','moment_ids':[ref]}]}
        errors=card_reference_problems(probe,refs,sensitivity)
        assert bool(errors)==(verdict=='blocked_public')
        if errors:
            settled,moved=demote_internal_cards(probe,refs,sensitivity)
            assert not settled['angles'] and len(settled['internal_insights'])==1 and len(moved)==1
        def when(seconds):
            seconds=int(seconds or 0)
            return f'{seconds//60}:{seconds%60:02d}'
        anchors=[span for span in m['source_evidence'] if span['span_id'] in m['anchor_span_ids']]
        audits.append({'original_ref':ref,'moment_id':m['moment_id'],'verdict':verdict,'potential_point':point,
                       'reason':reason,'brief_and_offer_fit':fit,'retained_evidence_comparison':coverage,'guardrail':guardrail,
                       'moment_type':m['moment_type'],'effective_sensitivity':m['sensitivity'],
                       'consent_status':rows[m['moment_id']]['consent_status'],'evidence_class':rows[m['moment_id']]['evidence_class'],
                       'original_qualifications':m['qualifications'],'original_summary':m['context_summary'],
                       'anchor_evidence':[{'time':when(a['start_seconds']),'speaker':a.get('speaker'),'text':a['text']} for a in anchors],
                       'reference_guard_errors':errors})

    # Separate alternative: remove only scenes that the current consent AND reference guard prohibit in public angles.
    alt_refs=['S85','S129','S138','S139','S158','S162','S182']
    omitted={refs[ref] for ref in alt_refs}
    eligible={m['moment_id'] for m in packet if m['sensitivity']!='internal_only'}
    assert len(eligible)==169
    for mid in omitted:
        assert sensitivity[mid]=='internal_only' and rows[mid]['consent_status']=='internal_only'
        assert card_reference_problems({'angles':[{'rank':1,'moment_ids':[inv[mid]]}]},refs,sensitivity)
    selected_ids=[mid for mid in ids if mid not in omitted]
    selected_packet=[m for m in packet if m['moment_id'] not in omitted]
    assert eligible <= set(selected_ids)
    assert len(selected_ids)==284
    reduced=copy.deepcopy(request)
    reduced['messages'][ui]['content']=render(selected_packet)+suffix
    reports=[preflight(r,JsonStore(OUT/'artifacts')) for r in (request,reduced)]
    assert not reports[0]['fits'] and reports[1]['fits']
    # Compare complete public-eligible dialogue/handling blocks; scene-reference numbers are expected to change.
    def blocks(req,source_packet):
        text=req['messages'][ui]['content'].split(PEOPLE_LABEL)[0]
        matches=list(re.finditer(r'^## Scene (S\d+) \(recording:.*$',text,re.M))
        mapping=scene_references(source_packet)
        return {mapping[hit.group(1)]:text[hit.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
                for i,hit in enumerate(matches)}
    old_blocks,new_blocks=blocks(request,packet),blocks(reduced,selected_packet)
    assert all(old_blocks[mid]==new_blocks[mid] for mid in eligible)
    new_refs=scene_references(selected_packet)
    new_sensitivity={m['moment_id']:m['sensitivity'] for m in selected_packet}
    new_inverse={mid:ref for ref,mid in new_refs.items()}
    assert all(not card_reference_problems({'angles':[{'rank':1,'moment_ids':[new_inverse[mid]]}]},new_refs,new_sensitivity) for mid in eligible)
    public_omitted_original=[a['original_ref'] for a in audits if not a['reference_guard_errors']]
    validation_path=OUT/'local-validation-284.json'
    rehearsed=validation_path.exists() and json.loads(validation_path.read_text(encoding='utf-8')).get('passed') is True
    rehearsal_note=('The exact 284-scene list passed the focused isolated PostgreSQL read/retry/restoration rehearsal; model and full downstream execution remain untested.'
                    if rehearsed else 'This alternative has no local database rehearsal yet; the previous seven checks applied to the earlier 268-scene proposal.')
    report={'run_id':snapshot['run']['run_id'],'offline_only':True,'production_changes':False,'model_calls':0,
            'audited_prompt_profile':snapshot['run']['input_refs']['angle_prompt_profile'],
            'template_matches_saved_request':True,'saved_system_sha256':hashlib.sha256(request['messages'][0]['content'].encode()).hexdigest(),
            'previous_proposal_recommendation':'Do not apply the 23-scene cut as previously proposed.',
            'judgment_limit':'This audit establishes eligibility and plausible angle paths, not which cards a stochastic provider would actually choose.',
            'verdict_counts':dict(Counter(a['verdict'] for a in audits)),
            'original_omissions_public_eligible':public_omitted_original,'audits':audits,
            'alternative':{'proposal_only':True,'original_verified':291,'selected':284,'omitted':7,
                           'all_public_eligible_scenes_preserved':True,'public_eligible_count':169,
                           'internal_only_before':122,'internal_only_after':115,
                           'selected_ids':selected_ids,
                           'omissions':[{'original_ref':ref,'moment_id':refs[ref],'summary':byid[refs[ref]]['context_summary'],
                                         'sensitivity':sensitivity[refs[ref]],'consent_status':rows[refs[ref]]['consent_status'],
                                         'reason':'Current consent and code forbid this scene in public cards; omit from this request only, preserving its record.'} for ref in alt_refs],
                           'original_preflight':reports[0],'reduced_preflight':reports[1],
                           'byte_reduction':reports[0]['input_token_budget_allowance']-reports[1]['input_token_budget_allowance'],
                           'public_scene_blocks_verified_identical_except_reference_number':169,
                           'limits':['Internal insights lose the seven omitted scenes and some context.',
                                     'Other context changes can still change model choices; exact output equivalence is not guaranteed.',
                                     'Current production status/consent and the final live preflight must be checked again before any separately approved operation.',
                                     rehearsal_note]}}
    save('angle-eligibility-audit.json',report)
    save('angle-preserving-alternative.json',report['alternative'])
    save('angle-preserving-alternative-request.json',reduced)
    save('angle-preserving-alternative-preflight.json',reports[1])
    lines=['# Prompt-aware audit of the proposed 23 omissions','','**Conclusion: do not apply the original 23-scene cut.** Nineteen omitted scenes are eligible for public consideration; eleven have a clear plausible process/client-experience angle, six can support one, and two are weak but not provably unused. Four are blocked from public angles by the current consent and validator.','',
           'This is an offline reading of the exact saved failed request: strategist v9, its assembled knowledge base, the frozen strategy brief, original scene dialogue and handling, plus the actual public-reference validation code. No production or model requests were made.','',
           '## Why the previous editorial filter was too broad','',
           '- The five tests allow a WIA belief, WIA standard or client experience. They do not restrict public evidence to measured outcomes.',
           '- The instructions explicitly accept opinions, recommendations, descriptions of WIA work and working rules without measured results.',
           '- The KB names onboarding, messaging interviews, Day in the Vault and Office Hours as behind-the-scenes sources. Routine-looking process evidence can therefore be valuable.',
           '- A scene outside brief beliefs B1-B5 may still become a card with belief_ref none. Accelerator offers remain open even while the current plan emphasizes ELEVATE.',
           '- A question can carry the human moment; the type label is not an eligibility score. S289 is labeled question but is explicitly delivered as public-usable team-practice evidence.',
           '- Keeping one scene per document is not enough. A public card can combine scenes from a single conversation, and the omitted scene can supply the response or process that makes a retained human line meaningful.',
           '- Internal-only is different: the code rejects those references in public cards and demotes them after repair. Anonymising or omitting figures does not remove the current consent restriction.','',
           '## Findings for every originally proposed omission','',
           '| Original scene | Finding | Possible point or restriction |','|---|---|---|']
    labels={'retain_strong':'Retain: clear potential','retain_supporting':'Retain: useful supporting evidence','weak_but_not_proven_unused':'Weak, not proven unused','blocked_public':'Public use blocked'}
    lines += [f"| {a['original_ref']} | {labels[a['verdict']]} | {a['potential_point']} |" for a in audits]
    lines += ['','## Detailed reasoning and original evidence','']
    for a in audits:
        lines += [f"### {a['original_ref']} — {a['moment_id']}",f"**{labels[a['verdict']]}**. Type: {a['moment_type']}; effective sensitivity: {a['effective_sensitivity']}; consent: {a['consent_status']}; evidence class: {a['evidence_class']}.",'',
                  '**Possible point:** '+a['potential_point'],'','**Why:** '+a['reason'],'','**Brief and offer fit:** '+a['brief_and_offer_fit'],'',
                  '**What retained scenes do or do not preserve:** '+a['retained_evidence_comparison'],'','**Limits:** '+a['guardrail'],'',
                  '**Original qualifications:** '+'; '.join(a['original_qualifications']),'']
        lines += [f"> [{q['time']}] {q['speaker']}: {q['text']}" for q in a['anchor_evidence']]
        lines += ['']
    alt=report['alternative']; after=reports[1]
    lines += ['## Separate safer alternative — not applied','',
              'Retain **all 169 scenes currently eligible for public consideration**. Omit only seven currently internal-only scenes with matching internal-only consent: '+', '.join(alt_refs)+'.',
              '',f"That leaves 284 of 291 verified scenes, including 115 of 122 internal-only scenes. It saves {alt['byte_reduction']:,} bytes. Allowance plus margin is {after['input_token_budget_allowance']+after['unmeasured_provider_margin_tokens']:,}, below {after['prompt_limit_reference_tokens']:,}; the existing preflight passes.",
              '', 'All 169 public-eligible dialogue/handling blocks were compared against the original request and are identical except for regenerated scene-reference numbers. The reference guard accepts all 169 under the new references. This is an eligibility check, not a finding that each passes all five editorial tests or becomes an angle.',
              '', 'This protects public source availability better than predicting which eligible scenes the model will choose. It still reduces internal insights and can change the model\'s ranking through context changes. No prompt audit, or even a paid A/B generation, can guarantee exactly identical stochastic outputs.',
              '', rehearsal_note+' No production operation is authorized by this audit.','']
    (OUT/'angle-eligibility-audit.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'verdict_counts':report['verdict_counts'],'original_omissions_public_eligible':len(public_omitted_original),
                      'alternative_selected':len(selected_ids),'alternative_omitted':alt_refs,
                      'public_eligible_preserved':169,'byte_reduction':alt['byte_reduction'],
                      'allowance':after['input_token_budget_allowance'],
                      'allowance_plus_margin':after['input_token_budget_allowance']+after['unmeasured_provider_margin_tokens'],
                      'prompt_limit':after['prompt_limit_reference_tokens'],'fits':after['fits']},indent=2))

if __name__=='__main__':
    main()
