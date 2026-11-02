// Exercise the compiled TypeScript processor with Buffer and plain-array inputs.
const assert = require('node:assert/strict');
const { processEntity } = require('../../runtimes/typescript/dist/runtimes/typescript/main.js');
for (const version of ['v1', 'v2']) {
  for (const bytes of [Buffer.from('0a0561', 'hex'), Uint8Array.from([10, 5, 97])]) {
    assert.throws(() => processEntity(bytes, version), /range|bounds/i);
  }
  for (const bytes of [Buffer.from('0a0141', 'hex'), Uint8Array.from([10, 1, 65])]) {
    assert.deepEqual(processEntity(bytes, version).fields,
      version === 'v1' ? { entity_id: 'A', name: '' } : { entity_id: 'A' });
  }
}
console.log('PASS: v1/v2 Buffer and Uint8Array truncated fields reject; complete fields decode');
