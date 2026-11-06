from __future__ import annotations

from datetime import datetime, UTC
from psycopg.types.json import Jsonb
from .contracts import signature_from_fields, AngleDraft
from .strategy_contracts import StrategicAngleDraft, StrategicQuality
from .models import Quality
from .repository import identifier, insert
from .store import canonical_hash
from .settings_store import snapshot_refs
from .angle_workflow import WORKFLOW
from .card_contracts import AngleCardV5, AngleCardV7, card_contract_for, card_point, is_v7, takes_public_stance
from .matching import is_card
from .cycle.verification import blocking
from .gates.roles import access_for, access_in
from .settings_store import value as setting
from .errors import NeedsInput

# "Decide in development" (R46, D5): stored as this exact object so migration 001's NOT NULL rule still holds.
DECIDE_IN_DEVELOPMENT = {'choice':'decide_in_development'}
# A card's rank and grounding are fixed by its run; an edit may change only the card's text.
CARD_EDITABLE = (set(AngleCardV5.model_fields) | set(AngleCardV7.model_fields)) - {'rank','moment_ids'}
# Flags a card cannot be developed past by acknowledgement: it is reframed (a new version, a new ledger) or marked internal.
# An internal figure or an invented name (L.B5), and strategist v7's public-use rejections (E.B30).
NOT_ACKNOWLEDGEABLE = ('internal_item', 'invented_person', 'point_is_tactic', 'takeaway_instructs', 'frustration_framing')


def require(repo, actor, capability):
    """Gate 1 roles (S.B3, R28, N4), checked in every mode and for every kind of angle, cards included.

    'decide' (approve, reject, and moving readiness out of research_required) needs the approver role;
    'edit' (edit, rescore, reassess) needs the editor role (an approver holds it too). Actors are verified emails (R37).
    """
    if capability not in ('decide','edit'):
        raise ValueError('Unknown Gate 1 capability')
    # The roles come from gates/roles.py (0.B9): the users table, else the legacy lists.
    if not actor or not access_for(repo.settings,actor).can(capability):
        raise PermissionError('Gate 1 ' + ('decisions require an approver' if capability == 'decide'
                              else 'edits require an editor or approver') + ' (ATELIER_BRIEF_APPROVERS, ATELIER_BRIEF_EDITORS)')


def cta_kind(cta, *, card):
    """'text' for a written CTA; 'decide_in_development' is accepted for strategist cards only."""
    if card and cta==DECIDE_IN_DEVELOPMENT:
        return 'decide_in_development'
    if isinstance(cta,dict) and isinstance(cta.get('text'),str) and cta['text'].strip():
        return 'text'
    raise NeedsInput('A selected CTA is required' + (' (or {"choice": "decide_in_development"})' if card else ''))


def check_card_approval(card, verified, moment_sensitivity, ledger=None, note=None, stance_confirmation=None, *, one_click=False):
    """The card rule beyond matching (E.B16 b, E.B10): every verify-before-publishing item acknowledged, no blocking
    ledger flag left unresolved, and no internal-only scene.

    Strategist v7 (E.B30, D31): a card rejected for public use (its point is a tactic, its takeaway instructs the reader, or
    it presents ads or an offer as frustrating) is reframed or marked internal, never acknowledged past; and a card that takes
    a public stance is developed only after an approver confirmed that stance (`confirm_stance`).

    A blocking flag (an unsupported fact, misattribution or consent) is resolved by reframing the card, which builds a
    new ledger, or by an approver acknowledging that flag by its ID with a note saying how it was checked.

    With `one_click` (the setting gates.one_click) the approval itself is the acknowledgement and the stance's confirmation; a
    public-use rejection and an internal or refused scene still stop it.
    """
    if one_click:
        verified = [*card['verify_before_publishing'], *(f['id'] for f in blocking(ledger))]
        note = note or 'Approved with one click'
        stance_confirmation = {'stance': (card.get('public_stance') or {}).get('stance'), 'point': card_point(card)}
    missing = [item for item in card['verify_before_publishing'] if item not in set(verified or [])]
    if missing:
        raise ValueError('Acknowledge every verify-before-publishing item before approval: ' + '; '.join(missing))
    # An internal figure or an invented name is never cleared by acknowledgement: the card is reframed (L.B5).
    fixed = [f for f in blocking(ledger) if f.get('kind') in NOT_ACKNOWLEDGEABLE]
    if fixed:
        raise ValueError('Reframe this card first, or mark it internal; an internal figure, an invented name or a public-use '
                         'rejection cannot be acknowledged: ' + '; '.join(f"{f['id']}: {f['message']}" for f in fixed))
    if takes_public_stance(card) and not stance_matches(card, stance_confirmation):
        raise ValueError('This card takes a public stance ("' + ((card.get('public_stance') or {}).get('stance') or card_point(card) or '')
                         + '"); an approver confirms the stance before the card is developed (D31): POST /storage/angles/{id}/stance')
    open_flags = [f for f in blocking(ledger) if f['id'] not in set(verified or [])]
    if open_flags:
        raise ValueError('Resolve every blocking ledger flag before developing this card (reframe it, or check each '
                         'against the call and acknowledge it): ' + '; '.join(f"{f['id']}: {f['message']}" for f in open_flags))
    if blocking(ledger) and not (note or '').strip():
        raise NeedsInput('Acknowledging a blocking ledger flag needs a note saying how it was checked')
    internal = sorted(mid for mid,sensitivity in moment_sensitivity.items() if sensitivity=='internal_only')
    if internal:
        raise ValueError('A card that uses an internal-only scene cannot be approved for public content: ' + ', '.join(internal))
    refused = sorted(mid for mid,sensitivity in moment_sensitivity.items() if sensitivity=='do_not_use')
    if refused:
        raise ValueError('A card that uses a scene whose client asked not to be used cannot be approved: ' + ', '.join(refused))


def stance_matches(card, confirmation) -> bool:
    """Whether a stance confirmation covers this card's stance as it stands (an edited stance needs a new confirmation)."""
    return bool(confirmation) and confirmation.get('stance') == (card.get('public_stance') or {}).get('stance') \
        and confirmation.get('point') == card_point(card)


def edited_card_body(body, changes):
    """Validate an edit against the card's own contract and rewrite content_body.card with the fields derived from it (E.B16 c)."""
    # Version 7 cards carry a point (E.B30), versions 5 and 6 a series (E.B21); earlier cards keep the version 3 and 4 contract.
    contract = card_contract_for(body['card'])
    if is_v7(body['card']) and 'core_perspective' in changes:
        # A screen built for v3 to v6 cards edits "the point" as core_perspective; on a v7 card it is `point`.
        changes = {**{k: v for k, v in changes.items() if k != 'core_perspective'}, 'point': changes['core_perspective']}
    editable = set(contract.model_fields) - {'rank','moment_ids'}
    if not changes or set(changes)-editable:
        raise ValueError('Card edits may change only the card text fields: ' + ', '.join(sorted(editable)))
    card = contract.model_validate({**body['card'],**changes}).model_dump(mode='json')
    point = card_point(card)
    return {**body,'card':card,'title':card['title'],'argument':point,'take':point,
            'audience':card['audience'],'mechanism':card['wia_in_action'] or point}


def comparison_owned(conn, angle_id):
    # Follow immutable provenance rather than a mutable score/status field. An
    # edit or rescore cannot convert comparison-only content into legacy content.
    return bool(conn.execute("""WITH RECURSIVE lineage AS (
        SELECT angle_id,run_id,supersedes_id FROM content_angles WHERE angle_id=%s
        UNION SELECT a.angle_id,a.run_id,a.supersedes_id FROM content_angles a
        JOIN lineage l ON a.angle_id=l.supersedes_id)
        SELECT 1 FROM lineage l JOIN pipeline_runs r ON r.run_id=l.run_id
        WHERE r.input_refs->>'workflow'=%s LIMIT 1""",(angle_id,WORKFLOW)).fetchone())


def locked(conn, angle_id, expected_hash, allowed_children=()):
    a = conn.execute('SELECT * FROM content_angles WHERE angle_id=%s FOR UPDATE',(angle_id,)).fetchone()
    if not a or a['content_hash']!=expected_hash:
        raise ValueError('Angle changed; refresh before saving')
    if any(r['angle_id'] not in allowed_children for r in conn.execute('SELECT angle_id FROM content_angles WHERE supersedes_id=%s',(angle_id,))):
        raise ValueError('A replacement already exists; refresh before saving')
    return a


def edit(repo, angle_id, expected_hash, changes, actor, note=None):
    require(repo, actor, 'edit')
    allowed = {'title','argument','audience','tension','take','mechanism','reader_decision','source_assertions','inference','qualifiers','risks'}
    strategic_fields = set(StrategicAngleDraft.model_fields) - {'local_key', 'moment_ids', 'quality'}
    allowed |= strategic_fields
    legacy_fields = bool(changes) and not set(changes)-allowed
    if not legacy_fields and (not changes or set(changes)-CARD_EDITABLE):
        raise ValueError('Invalid editable fields')
    with repo.connection() as conn:
        a = locked(conn,angle_id,expected_hash)
        if is_card(a['content_body']):
            return save_card_edit(repo,conn,a,changes,actor,note)
        if not legacy_fields:
            raise ValueError('Invalid editable fields')
        body = {**a['content_body'],**changes}
        moments = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(angle_id,))]
        if a['content_body'].get('strategy'):
            if set(changes) - strategic_fields:
                raise ValueError('Edit the strategic perspective fields rather than legacy Argument/Take aliases')
            if (a['content_body']['strategy'].get('evidence_readiness') == 'research_required'
                    and changes.get('evidence_readiness', 'research_required') != 'research_required'):
                # Readiness leaves research_required only through an approver action with a note (S.B3).
                require(repo, actor, 'decide')
                if not note or not note.strip():
                    raise NeedsInput('Moving an opportunity out of research_required needs a note explaining the evidence')
            draft = StrategicAngleDraft.model_validate({**a['content_body']['strategy'], **changes,
                                                        'local_key':'editor', 'moment_ids':moments})
            data = draft.model_dump(mode='json')
            body = {**a['content_body'], 'strategy':data,
                'title':data['title'], 'argument':data['core_perspective'], 'take':data['core_perspective'],
                'audience':data['audience'], 'tension':data['tension'],
                'mechanism':data['wia_expertise_in_action'] or data['core_perspective'],
                **{k:data[k] for k in ('reader_decision','source_assertions','inference','qualifiers','risks')}}
        else:
            if set(changes) - set(AngleDraft.model_fields):
                raise ValueError('Legacy content requires legacy editable fields')
            scores = a['quality_scores'] or {'grounding':0.,'source_relevance':0.,'audience_fit':0.,'specificity':0.,'editorial_usefulness':0.,'reasons':['Pending editor review']}
            AngleDraft.model_validate({**body,'local_key':'editor','moment_ids':moments,
                                      'quality':{k:scores[k] for k in ('grounding','source_relevance','audience_fit','specificity','editorial_usefulness','reasons')}})
        if any(not any(s.startswith(f'[{m}] ') for m in moments) for s in body['source_assertions']):
            raise ValueError('Assertions must retain a referenced moment prefix')
        for row in conn.execute('SELECT moment_body FROM key_moments WHERE moment_id=ANY(%s)',(moments,)):
            if not set(row['moment_body']['qualifications']).issubset(body['qualifiers']):
                raise ValueError('Source qualifications must be retained')
        new_id = identifier('angle')
        same_input = signature_from_fields(body)==signature_from_fields(a['content_body'])
        insert(conn,'content_angles',{'angle_id':new_id,'week_id':a['week_id'],'run_id':a['run_id'],'supersedes_id':angle_id,
               'content_body':body,'content_hash':canonical_hash({'body':body,'moments':moments}),
               'first_generated_at':a['first_generated_at'],'updated_by':actor,
               'embedding':a['embedding'] if same_input else None,
               'embedding_input_hash':a['embedding_input_hash'] if same_input else None})
        for m in moments:
            insert(conn,'angle_moments',{'angle_id':new_id,'moment_id':m,'evidence_role':'supports_argument'})
        repo.event(conn,a['run_id'],'angle_edited','Gate 1 edit saved; quality and matching require reassessment',
                   details={'angle_id':new_id,'supersedes_id':angle_id,'actor':actor,**({'note':note} if note else {})})
        return {'angle_id':new_id,'content_hash':canonical_hash({'body':body,'moments':moments})}


def save_card_edit(repo, conn, a, changes, actor, note=None, *, decided=False, by_person=True, provenance=None):
    """A new card version superseding the old one; matching must run again before approval (no self-score involved).

    Removing or rewording a verify-before-publishing item, or editing a held card (which lifts the hold), changes what
    the approver must check or decided, so it needs an approver and a note (S.B3). `decided` marks a call made by an
    approver's recorded disposition (a reframe), which carries its own decision row, or a refresh whose request was
    checked when it was queued.

    `content_body.person_edits` names every card field a person has written, carried from version to version, so a
    refresh with feedback keeps those fields word for word (3.B7, cycle/refresh.py). A person's edit (`by_person`) adds the
    fields whose text it changed; a model's version (a refresh) adds none and carries `provenance`, its maker's record
    (R58), which a later version drops.
    """
    body = edited_card_body(a['content_body'],changes)
    old_card = a['content_body']['card']
    written = sorted(set(a['content_body'].get('person_edits') or [])
                     | ({f for f in changes if old_card.get(f)!=body['card'].get(f)} if by_person else set()))
    body.pop('person_edits',None); body.pop('refresh',None)
    if written:
        body['person_edits'] = written
    if provenance:
        body['refresh'] = provenance
    removed = [i for i in a['content_body']['card']['verify_before_publishing'] if i not in body['card']['verify_before_publishing']]
    held = a['content_body'].get('gate_one_hold')
    if (removed or held) and not decided:
        require(repo, actor, 'decide')
        if not (note or '').strip():
            raise NeedsInput('Removing a verify-before-publishing item or editing a held card needs a note saying why')
    moments = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(a['angle_id'],))]
    # A new version is new text: its own ledger (deterministic pass; E.B10), and no hold carried over. A stance confirmation
    # carries over only while the stance and the point are unchanged (D31).
    body.pop('gate_one_hold',None)
    if body.get('stance_confirmation') and not stance_matches(body['card'],body['stance_confirmation']):
        body.pop('stance_confirmation')
    if 'ledger' in body:
        from .cycle.verification import carry_forward, ledger_from_database
        from .cycle.strategy_brief import for_run
        # The model pass never runs again on this card: keep what it found in the text the edit left alone (E.B10). The
        # cycle's strategy brief checks the new text against the offer calendar again (E.B28).
        body['ledger'] = carry_forward(a['content_body'].get('ledger'),a['content_body']['card'],body['card'],
                                       ledger_from_database(conn,body['card'],strategy_brief=for_run(conn,a['run_id'])))
    new_id = identifier('angle')
    digest = canonical_hash({'body':body,'moments':moments})
    same_input = signature_from_fields(body)==signature_from_fields(a['content_body'])
    insert(conn,'content_angles',{'angle_id':new_id,'week_id':a['week_id'],'run_id':a['run_id'],'supersedes_id':a['angle_id'],
           'content_body':body,'content_hash':digest,'first_generated_at':a['first_generated_at'],'updated_by':actor,
           'embedding':a['embedding'] if same_input else None,
           'embedding_input_hash':a['embedding_input_hash'] if same_input else None})
    for m in moments:
        insert(conn,'angle_moments',{'angle_id':new_id,'moment_id':m,'evidence_role':'supports_argument'})
    repo.event(conn,a['run_id'],'angle_edited','Gate 1 card edit saved; matching requires reassessment',
               details={'angle_id':new_id,'supersedes_id':a['angle_id'],'actor':actor,'fields':sorted(changes),
                        'by':'person' if by_person else 'refresh',
                        **({'verify_removed':removed} if removed else {}),**({'hold_lifted':held} if held else {}),
                        **({'note':note} if note else {})})
    # The new version needs its own comparison check before it can be developed: queued now, not left to a manual step.
    return {'angle_id':new_id,'content_hash':digest,'check':queue_card_check(repo,conn,a['week_id'],actor)}


def rescore(repo, angle_id, expected_hash, scores, actor):
    require(repo, actor, 'edit')
    if 'strategic_fit' in scores and 'source_relevance' not in scores:
        s = StrategicQuality.model_validate(scores)
        q = Quality(grounding=s.grounding,source_relevance=s.source_strength,audience_fit=s.audience_resonance,
                    specificity=s.distinctiveness,editorial_usefulness=s.strategic_fit,reasons=s.reasons,
                    strategic_fit=s.strategic_fit,distinctiveness=s.distinctiveness,
                    audience_resonance=s.audience_resonance,source_strength=s.source_strength)
    else:
        q = Quality.model_validate(scores)
    if not q.reasons:
        raise ValueError('Editor quality assessment requires a reason')
    with repo.connection() as conn:
        a = locked(conn,angle_id,expected_hash)
        if is_card(a['content_body']):
            raise ValueError('Strategist cards are ranked, not scored; edit the card instead of rescoring it')
        if a['content_body'].get('strategy') and q.strategic_fit is None:
            raise ValueError('Strategic opportunities require a strategic quality assessment')
        if a['approval_status']=='approved':
            raise ValueError('Replace approved content before changing its assessment')
        conn.execute("""UPDATE content_angles SET quality_scores=%s,base_score=%s,adjusted_score=NULL,
            matching_result=NULL,selection_status='candidate',updated_by=%s,updated_at=now() WHERE angle_id=%s""",
            (Jsonb(q.model_dump(mode='json')),q.score(),actor,angle_id))
        repo.event(conn,a['run_id'],'angle_quality_reviewed','Editor quality assessment saved',details={'angle_id':angle_id,'actor':actor,'reasons':q.reasons})
        intent = canonical_hash([angle_id,expected_hash,q.model_dump(mode='json')])
        insert(conn,'pipeline_jobs',{'job_id':'editor_'+intent[:24],'run_id':a['run_id'],'week_id':a['week_id'],
               'angle_id':angle_id,'stage':'angle_editor_validation','status':'completed',
               'idempotency_key':'editor:'+intent,'result_refs':{'angle_ids':[angle_id],'actor':actor},
               'finished_at':datetime.now(UTC)},conflict=True)


def check_cohort(conn, report):
    """The comparison report's frozen assessment must still be complete for the cohort as it stands now."""
    from .matching import assess
    import copy
    snapshot=report['assessment_snapshot']; approval_view=copy.deepcopy(snapshot)
    # Prior family approvals bind an added CTA hash. Their body, quality,
    # grounding and vectors still have to match the original snapshot.
    for frozen in approval_view['candidates']:
        sibling=conn.execute('SELECT approval_status,matching_result,content_hash FROM content_angles WHERE angle_id=%s',(frozen['id'],)).fetchone()
        if sibling and sibling['approval_status']=='approved':
            from .briefs.inputs import angle_packet
            angle_packet(conn,frozen['id'])
            if (sibling['matching_result'] or {}).get('approval_policy',{}).get('snapshot_hash')!=canonical_hash(snapshot):
                raise ValueError('Approved cohort member has a different assessment policy')
            frozen['hash']=sibling['content_hash']
    assessed=assess(conn,approval_view,snapshot['contract'])
    if assessed['status']!='complete': raise ValueError('Current comparison coverage is incomplete')


def card_policy(conn, angle_id):
    """Comparison-owned cards (E.B16 j): approvable from the latest complete card assessment, without a scenario
    cutoff or selected_ids membership. A collapsed or superseded card is not approvable."""
    completed=conn.execute("SELECT run_id,result_refs FROM pipeline_jobs WHERE stage='angle_final_assessment' AND status='completed' AND result_refs->'candidate_ids' ? %s ORDER BY updated_at DESC LIMIT 1",(angle_id,)).fetchone()
    if not completed or completed['result_refs'].get('selection_basis')!='card_rank':
        raise ValueError('Card assessment is incomplete')
    report=completed['result_refs']
    if angle_id not in report['selection']['visible_ids']:
        raise ValueError('Card is collapsed into a better-ranked card or superseded by an edit')
    check_cohort(conn,report)
    family=next(f for f in report['families'] if angle_id in {f['original_id'],f.get('replacement_id')})
    return {'rule':'card_rank_v1','assessment_run_id':completed['run_id'],'snapshot_hash':canonical_hash(report['assessment_snapshot']),
            'family_original_id':family['original_id'],'selected_id':angle_id,'refinement_children':[]}


def decide(repo,angle_id,expected_hash,decision,cta,overlap_ack,note,actor,*,verified=None,record=None):
    """Approve or reject. record(conn, angle_row), when given, writes the disposition rows (E.B20) in the same transaction."""
    if decision not in {'approved','rejected'}:
        raise ValueError('Unknown Gate 1 decision')
    require(repo, actor, 'decide')
    with repo.connection() as conn:
        # Built on material removed at a client's request (6.B12): the card is marked, never developed.
        from .removal import mark_of
        if decision=='approved' and mark_of(conn,'angle',angle_id):
            raise ValueError("This card is built on material removed at a client's request; it cannot be developed")
        policy=None; scenario=None
        owned=decision=='approved' and comparison_owned(conn,angle_id)
        current=conn.execute('SELECT content_body FROM content_angles WHERE angle_id=%s',(angle_id,)).fetchone() if owned else None
        if owned and current and is_card(current['content_body']):
            policy=card_policy(conn,angle_id)
        elif owned:
            cutoff=repo.settings.angle_approval_cutoff
            if cutoff not in {.78,.85,.90}:
                raise ValueError('Comparison-only approval is disabled: authoritative threshold selection is pending')
            completed=conn.execute("SELECT run_id,result_refs FROM pipeline_jobs WHERE stage='angle_final_assessment' AND status='completed' AND result_refs->'candidate_ids' ? %s ORDER BY updated_at DESC LIMIT 1",(angle_id,)).fetchone()
            if not completed: raise ValueError('Comparison assessment is incomplete')
            report=completed['result_refs']
            scenario=next((s for s in report['scenarios'] if s['cutoff']==cutoff),None)
            if not scenario or angle_id not in scenario['selected_ids']: raise ValueError('Angle is not selected under the authoritative family scenario')
            check_cohort(conn,report)
            snapshot=report['assessment_snapshot']
            family=next(f for f in report['families'] if angle_id in {f['original_id'],f.get('replacement_id')})
            policy={'cutoff':cutoff,'assessment_run_id':completed['run_id'],'snapshot_hash':canonical_hash(snapshot),
                'family_original_id':family['original_id'],'selected_id':angle_id,
                'refinement_children':[family['replacement_id']] if family.get('replacement_id') else []}
        a = locked(conn,angle_id,expected_hash,(policy or {}).get('refinement_children',[]))
        card = is_card(a['content_body'])
        if decision=='approved' and (a['content_body'].get('strategy') or {}).get('evidence_readiness')=='research_required':
            raise ValueError('Source research is required before approving this opportunity for development')
        if a['approval_status']=='approved': raise ValueError('Angle has already been approved')
        if decision=='approved':
            result = a['matching_result'] or {}
            if result.get('status')!=('comparison_complete' if policy else 'complete') or result.get('candidate_hash')!=a['content_hash'] or (card or not policy) and a['selection_status']!='visible':
                raise ValueError('Approval requires current complete matching and a visible ' + ('card' if card else 'score'))
            if card:
                # No score to compare; the card rule replaces it (E.B16 b).
                # Consent stricter than the extractor's label decides (E.B16 f): do_not_use and internal_only block.
                from .cycle.verification import moment_handling
                sensitivity={r['moment_id']:moment_handling(r) for r in conn.execute(
                    'SELECT m.* FROM key_moments m JOIN angle_moments am USING(moment_id) WHERE am.angle_id=%s',(angle_id,))}
                one_click = setting('gates.one_click',conn)
                check_card_approval(a['content_body']['card'],verified,sensitivity,a['content_body'].get('ledger'),note,
                                    a['content_body'].get('stance_confirmation'),one_click=one_click)
                if one_click:
                    overlap_ack = True
                    if takes_public_stance(a['content_body']['card']) and not stance_matches(a['content_body']['card'],a['content_body'].get('stance_confirmation')):
                        # The approval confirms the stance: recorded as a confirmation would be, in the body the approval binds to.
                        a['content_body'] = {**a['content_body'],'stance_confirmation':{
                            'stance':(a['content_body']['card'].get('public_stance') or {}).get('stance'),'point':card_point(a['content_body']['card']),
                            'by':actor,'at':datetime.now(UTC).isoformat(),'note':'Confirmed by approving the card'}}
                        conn.execute('UPDATE content_angles SET content_body=%s WHERE angle_id=%s',(Jsonb(a['content_body']),angle_id))
            elif result.get('base_score')!=float(a['base_score']):
                raise ValueError('Quality assessment changed; reassess matching')
            flags=scenario['current_batch_flags'].get(angle_id,[]) if scenario else result.get('current_batch_flags',[])
            if card:
                flags=flags+result.get('historical_duplicates',[])
            if flags and (not overlap_ack or not note or not note.strip()):
                raise ValueError('Current-batch overlap requires an acknowledgement and distinct-treatment note')
            cta_kind(cta,card=card)
            # Bind CTA to approved content; it does not affect the semantic signature.
            moments = [r['moment_id'] for r in conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(angle_id,))]
            digest = canonical_hash({'body':a['content_body'],'moments':moments,'cta':cta})
            result = {**result,'candidate_hash':digest,'overlap_acknowledged':overlap_ack,'distinct_treatment_note':note,
                      **({'verification_acknowledged':list(a['content_body']['card']['verify_before_publishing']),
                          'ledger_flags_acknowledged':[f['id'] for f in blocking(a['content_body'].get('ledger'))]} if card else {})}
            if policy: result['approval_policy']=policy
            conn.execute("""UPDATE content_angles SET content_hash=%s,selected_cta=%s,approval_status='approved',
                approved_hash=%s,approved_by=%s,approved_at=now(),review_note=%s,matching_result=%s,updated_by=%s,updated_at=now()
                WHERE angle_id=%s""",(digest,Jsonb(cta),digest,actor,note,Jsonb(result),actor,angle_id))
        else:
            conn.execute("UPDATE content_angles SET approval_status='rejected',approved_hash=NULL,approved_by=NULL,approved_at=NULL,review_note=%s,updated_by=%s,updated_at=now() WHERE angle_id=%s",(note,actor,angle_id))
        repo.event(conn,a['run_id'],'gate_one_'+decision,'Gate 1 decision saved',details={'angle_id':angle_id,'actor':actor,'decision':decision})
        response={'angle_id':angle_id,'approval_status':decision}
        if record:
            response['decision_id']=record(conn,a)
        elif card and conn.execute("SELECT to_regclass('public.decisions') AS t").fetchone()['t']:
            # A card approved or rejected without a disposition is still one decision and one label (R45), so the
            # decision log and the learning loop see it: an approval develops the card.
            from .gates.decisions import record as record_decision
            response['decision_id']=record_decision(conn,item_kind='angle',item_id=angle_id,week_id=a['week_id'],
                disposition='develop' if decision=='approved' else 'reject',action='gate_one_'+decision,actor=actor,
                author=actor,note=(note or '').strip() or None,expected_hash=expected_hash,details={'run_id':a['run_id']},
                settings=repo.settings)
        if decision=='approved' and repo.settings.brief_enabled:
            # Developing a card starts its brief live (4.B1); a spent standing budget makes it wait with the reason (6.B3).
            from .briefs.workflow import develop_mode, queue_in_transaction
            response['brief_run']=queue_in_transaction(repo,conn,angle_id,actor,develop_mode(repo.settings))
        return response


def confirm_stance(repo, angle_id, expected_hash, actor, note=None):
    """An approver confirms the public stance a strategist v7 card takes (D31, E.B30), so it can be developed.

    The confirmation is review state, like a hold: stored in content_body with who, when, the stance and the point it
    covers; the content hash, and the matching bound to it, are unchanged. An edit that changes the stance or the point
    drops it."""
    require(repo, actor, 'decide')
    with repo.connection() as conn:
        a = locked(conn,angle_id,expected_hash)
        card = (a['content_body'] or {}).get('card')
        if not card or not takes_public_stance(card):
            raise ValueError('This card takes no public stance; nothing to confirm')
        if a['approval_status']=='approved':
            raise ValueError('Angle has already been approved')
        confirmation = {'stance':(card.get('public_stance') or {}).get('stance'),'point':card_point(card),'by':actor,
                        'at':datetime.now(UTC).isoformat(),'note':(note or '').strip() or None}
        conn.execute("UPDATE content_angles SET content_body=content_body||jsonb_build_object('stance_confirmation',%s::jsonb),"
                     "updated_by=%s,updated_at=now() WHERE angle_id=%s",(Jsonb(confirmation),actor,angle_id))
        repo.event(conn,a['run_id'],'gate_one_stance_confirmed','Public stance confirmed',
                   details={'angle_id':angle_id,'actor':actor,'stance':confirmation['stance']})
        return {'angle_id':angle_id,'content_hash':a['content_hash'],'stance_confirmation':confirmation}


ACTIVE_SCOPES = ('weekly_angles','angle_reassessment','comparison_reassessment')


def reassess(repo,week_id,actor):
    require(repo, actor, 'edit')
    with repo.connection() as conn:
        week = conn.execute('SELECT * FROM weeks WHERE week_id=%s FOR UPDATE',(week_id,)).fetchone()
        if not week:
            raise ValueError('Week not found')
        if conn.execute("SELECT 1 FROM pipeline_runs WHERE week_id=%s AND run_scope=ANY(%s) AND status IN ('queued','running')",
                        (week_id,list(ACTIVE_SCOPES))).fetchone():
            raise ValueError('A run is already active for this week')
        return _queue_reassessment(repo,conn,week_id,actor)


def _queue_reassessment(repo,conn,week_id,actor,*,encoding_mode=None,card_check=False):
    """Encoding and matching for the week's current versions; generation never repeats. `encoding_mode` ('live' or
    'cached') is the embedding job's mode, as queue_encoding sets it; unset, the job reuses saved vectors only."""
    rows = conn.execute("""SELECT angle_id,content_hash FROM content_angles a WHERE week_id=%s AND NOT EXISTS
        (SELECT 1 FROM content_angles n WHERE n.supersedes_id=a.angle_id) ORDER BY angle_id""",(week_id,)).fetchall()
    if not rows:
        raise ValueError('No angles to reassess')
    comparison_rows = [a for a in rows if comparison_owned(conn,a['angle_id'])]
    if comparison_rows:
        if len(comparison_rows)!=len(rows):
            raise ValueError('Mixed legacy/comparison cohorts require a separate comparison run')
        return queue_comparison_reassessment(repo,conn,week_id,actor,rows,encoding_mode=encoding_mode,card_check=card_check)
    # A cycle over a date window reads documents that belong to no week (3.B2): its cards are checked against those.
    sources = repo.week_sources(conn,week_id)
    if not sources:
        raise ValueError('No calls are recorded for this week, so its cards cannot be checked')
    run_id = identifier('run')
    refs = {'transcripts':[{'id':t['transcript_id'],'hash':t['content_hash']} for t in sources],
            'angle_ids':[a['angle_id'] for a in rows],'angle_hashes':{a['angle_id']:a['content_hash'] for a in rows},
            'synthetic':repo.settings.synthetic,'mode':'synthetic' if repo.settings.synthetic else 'replay',
            'week_index':sources[0]['source_metadata'].get('week_index',0),
            # Documents a window cycle read are owned by no week; the worker accepts them as the cycle's selection.
            **({'selected_by':'window'} if any(s['week_id']!=week_id for s in sources) else {}),**({'card_check':True} if card_check else {}),
            **snapshot_refs('matching',storage=repo.settings,conn=conn)}
    insert(conn,'pipeline_runs',{'run_id':run_id,'week_id':week_id,'run_scope':'angle_reassessment',
           'trigger_type':'manual','triggered_by':actor,'input_refs':refs})
    prev = None
    for stage in ('angle_embedding','angle_matching'):
        job_id = identifier('job')
        insert(conn,'pipeline_jobs',{'job_id':job_id,'run_id':run_id,'week_id':week_id,'stage':stage,
               'idempotency_key':f'{run_id}:{stage}','progress_details':{'dependencies':[prev] if prev else [],
               **({'encoding_mode':encoding_mode} if encoding_mode and stage=='angle_embedding' else {})}})
        prev=job_id
    conn.execute("UPDATE weeks SET active_run_id=%s,status='queued' WHERE week_id=%s",(run_id,week_id))
    repo.event(conn,run_id,'reassessment_queued','Saved angles queued for encoding/matching; generation will not repeat')
    return {'run_id':run_id}


def check_encoding_mode(repo,conn,week_id,actor):
    """How a new card version's check embeds it: live only when the week's cycle ran live, live encoding is allowed and
    the actor is an approver (a live encode is an approver's action, S.B3), and then only under the worker's run plan
    (E.B1), which refuses it with its reason otherwise. Anything else reuses saved vectors and waits, visibly."""
    cycle = conn.execute("""SELECT input_refs->>'mode' AS mode FROM pipeline_runs WHERE week_id=%s AND run_scope='weekly_angles'
        ORDER BY created_at DESC LIMIT 1""",(week_id,)).fetchone()
    # The actor may be a run's recorded address (a refresh's worker, a deferred check): resolve it as the API would.
    live = (cycle or {}).get('mode')=='live' and repo.settings.encoding_enabled and access_in(conn,repo.settings,actor).can('decide')
    return 'live' if live else 'cached'


def queue_card_check(repo,conn,week_id,actor):
    """Queue the check a new card version needs before it can be developed (a reframe, a revive or an edit): its
    embedding, then matching and the duplicate check over the week (E.B16, E.B20). Called in the transaction that saves
    the version. A check that has not started yet is replaced by one that includes this version; while another run is
    working on the week, the check is deferred and the worker queues it when that run ends (queue_deferred_checks).
    The card's `check` in the week review says where it stands."""
    conn.execute('SELECT 1 FROM weeks WHERE week_id=%s FOR UPDATE',(week_id,))
    active = conn.execute("""SELECT run_id,run_scope FROM pipeline_runs WHERE week_id=%s AND run_scope=ANY(%s)
        AND status IN ('queued','running')""",(week_id,list(ACTIVE_SCOPES))).fetchall()
    unstarted = [r for r in active if r['run_scope']!='weekly_angles' and not conn.execute(
        "SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND status<>'queued' LIMIT 1",(r['run_id'],)).fetchone()]
    if len(unstarted)<len(active):
        return {'status':'deferred','message':'The week has a run in progress; this version is checked when it ends'}
    replaced = 'Replaced by a check that includes a newer card version'
    for r in unstarted:
        conn.execute("UPDATE pipeline_jobs SET status='cancelled',current_message=%s,finished_at=now() WHERE run_id=%s",(replaced,r['run_id']))
        conn.execute("UPDATE pipeline_runs SET status='cancelled',current_message=%s,finished_at=now(),updated_at=now() WHERE run_id=%s",
                     (replaced,r['run_id']))
    queued = _queue_reassessment(repo,conn,week_id,actor,encoding_mode=check_encoding_mode(repo,conn,week_id,actor),card_check=True)
    return {'status':'queued',**queued}


def uncovered_cards(conn,week_id):
    """The week's current card versions without complete matching that no run has taken in yet."""
    return [r['angle_id'] for r in conn.execute("""SELECT a.angle_id FROM content_angles a WHERE a.week_id=%s AND a.content_body ? 'card'
        AND NOT EXISTS (SELECT 1 FROM content_angles n WHERE n.supersedes_id=a.angle_id)
        AND (a.matching_result IS NULL OR a.matching_result->>'candidate_hash' IS DISTINCT FROM a.content_hash)
        AND NOT EXISTS (SELECT 1 FROM pipeline_runs r WHERE r.week_id=a.week_id AND r.status<>'cancelled'
            AND (r.input_refs->'angle_ids' ? a.angle_id OR r.run_id=a.run_id AND r.run_scope='weekly_angles'
                 AND a.supersedes_id IS NULL AND NOT a.content_body ? 'revived_from'))
        ORDER BY a.angle_id""",(week_id,))]


def card_check(angle, runs, jobs):
    """Where a card version's comparison check stands, for the card screen: checked, queued, running, waiting (for an
    embedding), failed (with the reason) or not queued. `runs` and `jobs` are the week's, newest run first."""
    matching = angle.get('matching_result') or {}
    if matching.get('candidate_hash')==angle['content_hash'] and matching.get('status') in ('complete','comparison_complete'):
        return {'status':'checked','run_id':None,'message':None}
    # The weekly run covers the cards it generated; a reframe, revive or edit is covered only by a later check.
    generated = not angle.get('supersedes_id') and not (angle.get('content_body') or {}).get('revived_from')
    run = next((r for r in runs if r['status']!='cancelled' and (angle['angle_id'] in ((r['input_refs'] or {}).get('angle_ids') or [])
                or generated and r['run_id']==angle['run_id'] and r['run_scope']=='weekly_angles')), None)
    if not run:
        active = any(r['status'] in ('queued','running') and r['run_scope'] in ACTIVE_SCOPES for r in runs)
        return {'status':'not_queued','run_id':None,'message':'Waiting for the run in progress on this week to end' if active
                else 'Not checked yet; reassess the week to check this version'}
    status = {'queued':'queued','running':'running','partially_completed':'waiting','failed':'failed'}.get(run['status'],'checked')
    failed = next((j for j in jobs if j['run_id']==run['run_id'] and j['status'] in ('failed','waiting')), None)
    message = (failed or {}).get('error_summary') or (failed or {}).get('current_message') or run.get('current_message')
    return {'status':status,'run_id':run['run_id'],'message':message if status in ('waiting','failed') else None}


def queue_deferred_checks(repo,conn,week_id):
    """When a run on the week ends, the worker queues the check a deferred card version is still waiting for."""
    waiting = uncovered_cards(conn,week_id)
    if not waiting or conn.execute("SELECT 1 FROM pipeline_runs WHERE week_id=%s AND run_scope=ANY(%s) AND status IN ('queued','running')",
                                   (week_id,list(ACTIVE_SCOPES))).fetchone():
        return None
    who = conn.execute('SELECT updated_by FROM content_angles WHERE angle_id=ANY(%s) ORDER BY updated_at DESC LIMIT 1',(waiting,)).fetchone()
    return queue_card_check(repo,conn,week_id,(who or {}).get('updated_by') or 'system')


def queue_comparison_reassessment(repo,conn,week_id,actor,leaves,*,encoding_mode=None,card_check=False):
    """A new assessment intent only; never issues generation or another Call 3."""
    families = []
    ids = set()
    for leaf in leaves:
        root = conn.execute("""WITH RECURSIVE lineage AS (
            SELECT angle_id,supersedes_id FROM content_angles WHERE angle_id=%s
            UNION SELECT a.angle_id,a.supersedes_id FROM content_angles a JOIN lineage l ON a.angle_id=l.supersedes_id)
            SELECT angle_id FROM lineage WHERE supersedes_id IS NULL""",(leaf['angle_id'],)).fetchone()['angle_id']
        ids.add(root); ids.add(leaf['angle_id'])
        families.append({'original_id':root,'replacement_id':leaf['angle_id'] if root!=leaf['angle_id'] else None,
                         'targeted':root!=leaf['angle_id'],'disposition':'manual_reassessment',
                         'explanation':'Saved family reassessed without another refinement pass'})
    candidates = conn.execute('SELECT angle_id,content_hash,content_body FROM content_angles WHERE angle_id=ANY(%s)',(list(ids),)).fetchall()
    # A card edit almost always changes its signature, so a synthetic test database may encode it with the fake provider.
    cards = all(is_card(a['content_body']) for a in candidates)
    moments = [r['moment_id'] for r in conn.execute('SELECT DISTINCT moment_id FROM angle_moments WHERE angle_id=ANY(%s)',(list(ids),))]
    sources = repo.week_sources(conn,week_id)
    if not sources:
        raise ValueError('No calls are recorded for this week, so its cards cannot be checked')
    run_id = identifier('run')
    refs = {'transcripts':[{'id':s['transcript_id'],'hash':s['content_hash'],
                           'view_hash':canonical_hash([s['original_text'],s['passage_map'],s['source_metadata']])} for s in sources],
            'angle_ids':sorted(ids),'angle_hashes':{a['angle_id']:a['content_hash'] for a in candidates},
            'moment_ids':moments,'families':families,'comparison_reassessment':True,'workflow':WORKFLOW,
            'synthetic':repo.settings.synthetic,'mode':'synthetic' if cards and repo.settings.synthetic else 'replay',
            'week_index':sources[0]['source_metadata'].get('week_index',0),
            # Documents a window cycle read are owned by no week; the worker accepts them as the cycle's selection.
            **({'selected_by':'window'} if any(s['week_id']!=week_id for s in sources) else {}),**({'card_check':True} if card_check else {}),
            **snapshot_refs('matching',storage=repo.settings,conn=conn)}
    insert(conn,'pipeline_runs',{'run_id':run_id,'week_id':week_id,'run_scope':'comparison_reassessment',
                                'trigger_type':'manual','triggered_by':actor,'input_refs':refs})
    previous = None
    for stage in ('history_context','angle_initial_embedding','angle_final_assessment'):
        jid = identifier('job')
        insert(conn,'pipeline_jobs',{'job_id':jid,'run_id':run_id,'week_id':week_id,'stage':stage,
               'idempotency_key':f'{run_id}:{stage}','progress_details':{'dependencies':[previous] if previous else [],
               **({'encoding_mode':encoding_mode} if encoding_mode and stage=='angle_initial_embedding' else {})}})
        previous = jid
    conn.execute("UPDATE weeks SET active_run_id=%s,status='queued' WHERE week_id=%s",(run_id,week_id))
    repo.event(conn,run_id,'comparison_reassessment_queued','New comparison intent; Gate 1 remains disabled')
    return {'run_id':run_id,'workflow':WORKFLOW}
