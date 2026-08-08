import assert from 'node:assert/strict';
import { displayName, dataUser } from '../dragon/display_names.js';

assert.equal(displayName('Kid1', { Kid1: 'Kid1' }), 'Kid1');
assert.equal(dataUser('Kid1', { Kid1: 'Kid1' }), 'Kid1');
assert.equal(displayName('Randy', { Kid1: 'Kid1' }), 'Randy');
assert.equal(displayName('Kid1', {}), 'Kid1');
assert.equal(displayName('', { Kid1: 'Kid1' }), '');
