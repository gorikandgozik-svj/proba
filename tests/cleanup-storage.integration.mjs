// Only for explicitly provisioned synthetic QA accounts, after removing their post/media rows.
import {createClient} from '@supabase/supabase-js';
let removed=0;
for(const name of ['A','B','C']){
 const email=process.env['NEXUS_TEST_EMAIL_'+name];if(!email?.startsWith('nexus-qa-')||!email.endsWith('@example.invalid'))throw new Error('Cleanup only supports dedicated nexus-qa-*@example.invalid accounts.');
 const db=createClient(process.env.NEXT_PUBLIC_SUPABASE_URL,process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,{auth:{persistSession:false}});
 const login=await db.auth.signInWithPassword({email,password:process.env.NEXUS_TEST_PASSWORD});if(login.error)throw login.error;const id=login.data.user.id;
 const files=await db.storage.from('nexus-media').list(id,{limit:1000});if(files.error)throw files.error;
 if(files.data.length){const result=await db.storage.from('nexus-media').remove(files.data.map(file=>id+'/'+file.name));if(result.error)throw result.error;removed+=files.data.length;}
 const logout=await db.auth.signOut({scope:'global'});if(logout.error)throw logout.error;
}
console.log(`Removed ${removed} synthetic QA media objects; all QA refresh sessions revoked.`);
