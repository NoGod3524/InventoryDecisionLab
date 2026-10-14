// Node standard-library checks for zero-demand display semantics (not visual QA).
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function execute(path,id,mutate){
 const html=fs.readFileSync(path,'utf8'),pattern=new RegExp('<script id="'+id+'" type="application/json">([\\s\\S]*?)<\\/script>');
 const data=JSON.parse(html.match(pattern)[1]);mutate(data);
 const nodes={};const get=id=>nodes[id]||={value:id==='seed'?'all':'95',textContent:'',innerHTML:'',append(){}};
 get(id).textContent=JSON.stringify(data);
 const sandbox={document:{getElementById:get,createElement:()=>({click(){}})},Intl,Blob,URL,setTimeout};
 vm.runInNewContext(html.split('<script>').pop().split('</script>')[0],sandbox);
 return {get,data};
}
for(const last of [false,true]){
 const {get,data}=execute('examples/base/report.html','data',d=>{
  const seeds=[...new Set(d.summaries.map(r=>r.seed))];let seed=last?seeds.at(-1):seeds[0];
  d.summaries.filter(r=>r.seed===seed).forEach(r=>r.fill_rate=null);
 });
 assert.match(get('cards').innerHTML,/4 valid \/ 1 undefined/);
 const expected=data.summaries.filter(r=>r.policy==='fixed_periodic'&&r.fill_rate!==null).reduce((s,r)=>s+r.fill_rate,0)/4;
 assert.ok(get('cards').innerHTML.includes((expected*100).toFixed(1)+'%'));
 assert.match(get('recommendation').textContent,/No policy/);
}
const {get}=execute('examples/robustness/report.html','evidence',d=>{
 d.selected='seasonal_buffer';d.summary.forEach(r=>{r.mean_fill=null;r.fill_lower=null;r.fill_upper=null;r.n_valid_fill=0;r.n_undefined_fill=r.n_seeds;r.share_meeting_95=0});
});
assert.match(get('cards').innerHTML,/N\/A/);assert.match(get('rows').innerHTML,/N\/A/);
assert.match(get('chart').innerHTML,/service undefined/);
console.log('Evidence smoke checks passed: undefined service excluded from means, counts disclosed, gates abstain, null charts labeled.');
