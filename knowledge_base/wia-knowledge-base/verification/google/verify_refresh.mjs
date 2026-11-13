/** Verify offline OAuth refresh without any mailbox/file mutation. */
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {config,storedTokens,storeTokens,tokenRequest,directory} from './oauth_store.mjs';
const report={started_at_utc:new Date().toISOString(),endpoint:'https://oauth2.googleapis.com/token',
 method:'POST',grant_type:'refresh_token',source_data_modifications:false};
try{
 const c=await config();const previous=await storedTokens();
 if(!previous?.refresh_token||previous.client_id!==c.clientId)throw new Error('matching_refresh_token_missing');
 const data=await tokenRequest({grant_type:'refresh_token',refresh_token:previous.refresh_token,
  client_id:c.clientId,client_secret:c.clientSecret});
 const updated=await storeTokens(data,c,previous);
 report.result='refresh_verified';report.http_status=200;
 report.granted_scopes=(updated.scope??'').split(' ').filter(Boolean);
 report.access_token_present=Boolean(updated.access_token);report.refresh_token_retained=Boolean(updated.refresh_token);
 report.expires_in_seconds=data.expires_in??null;
}catch(e){report.result='refresh_not_verified';report.error=e.message;report.oauth_error=e.oauthError??null;}
report.finished_at_utc=new Date().toISOString();
await writeFile(path.join(directory,'refresh_probe.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
