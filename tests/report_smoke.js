// Optional Node standard-library smoke test. No packages, browser, or network.
// This checks report execution and controls, not visual/browser layout.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const report = fs.readFileSync(process.argv[2] || 'examples/base/report.html', 'utf8');
const payload = report.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script = report.split('<script>').pop().split('</script>')[0];
const elements = {};
const element = id => elements[id] ||= {value: id === 'seed' ? 'all' : '95', textContent: '', innerHTML: '', append() {}};
element('data').textContent = payload;
const sandbox = {document: {getElementById: element, createElement: () => ({click(){}})},
    Intl, Blob, URL, setTimeout};
vm.runInNewContext(script, sandbox);
assert.match(element('cards').innerHTML, /Seasonal/);
assert.match(element('recommendation').textContent, /lowest-cost feasible/);
assert.match(element('frontier').innerHTML, /<svg/);
element('target').value = '100'; element('target').oninput();
assert.match(element('recommendation').textContent, /No policy/);
element('target').value = ''; element('target').oninput();
assert.match(element('recommendation').textContent, /between 0 and 100/);
element('target').value = '101'; element('target').oninput();
assert.match(element('recommendation').textContent, /between 0 and 100/);
element('seed').value = '7'; element('seed').onchange();
assert.match(element('rows').innerHTML, /Fixed periodic/);
element('download').onclick();
console.log('Report smoke checks passed: render, seed, target, infeasibility, invalid input, CSV export.');
