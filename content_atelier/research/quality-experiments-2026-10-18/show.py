import sys,json; sys.stdout.reconfigure(encoding='utf-8')
for rid in sys.argv[1:]:
    o=json.load(open(f'runs/{rid}.json',encoding='utf-8'))['output']
    print('='*20,rid)
    if 'week_summary' in o:
        print('SUMMARY:',o['week_summary'])
        for a in sorted(o['angles'],key=lambda x:x['rank']): print('\n',a['rank'],a['pillar'],a['content_type'],'|',a['title'],'\n  PERSPECTIVE:',a['core_perspective'],'\n  WHY:',a['why_it_matters'],'\n  WIA:',a['wia_in_action'],'\n  OFFER:',a['offer_connection'],'\n  MOMENTS:',a['moment_ids'],'\n  VERIFY:',a['verify_before_publishing'],'\n  SELECTED:',a['why_selected'])
        print('\nINTERNAL:'); [print(' -',i['insight'],'|',i['use']) for i in o['internal_insights']]
        print('\nNOT SELECTED:'); [print(' -',i['idea'],'|',i['reason']) for i in o['considered_not_selected']]
    else:
        for a in o['angles']: print('\n',a['strategic_purpose'],a['content_type'],'|',a['title'],'\n  OPP:',a['content_opportunity'],'\n  PERSPECTIVE:',a['core_perspective'],'\n  TENSION:',a['tension'],'\n  WIA:',a['wia_expertise_in_action'],'\n  AUD:',a['audience'],'\n  SERVICE:',a['service_relevance'],'\n  MOMENTS:',a['moment_ids'],'\n  QUAL:',len(a['qualifiers']),'RISKS:',len(a['risks']),'ASSERT:',len(a['source_assertions']),'\n  SCORES:',{k:v for k,v in a['quality'].items() if k!='reasons'},'\n  SELECTED:',a['selection_reason'])
        print('\nINTERNAL:'); [print(' -',i['insight']) for i in o['internal_insights']]
        print('\nCOVERAGE:'); [print(' -',c) for c in o['coverage_notes']]
