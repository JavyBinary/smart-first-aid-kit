import test from 'node:test';
import assert from 'node:assert/strict';

import { getApiBase } from '../src/api/client.js';
import { serializeCreateKitItem, serializeUpdateKitItem } from '../src/api/kit.api.js';
import { serializeHealthProfile, deserializeHealthProfile } from '../src/api/profile.api.js';

test('serializeCreateKitItem maps isPrescription to status and strips extra fields', () => {
    const raw = {
        id: 'local-123',
        name: ' Нурофен ',
        dosage: '400 мг',
        form: 'таблетки',
        category: 'Обезболивающие',
        isPrescription: true,
        iconColor: '#E8F7F0',
        tags: ['жар', ' боль ', ''],
        expiry: '2028-01-01',
    };

    const payload = serializeCreateKitItem(raw);
    assert.equal(payload.id, undefined);
    assert.equal(payload.iconColor, undefined);
    assert.equal(payload.isPrescription, undefined);
    assert.equal(payload.name, 'Нурофен');
    assert.equal(payload.status, 'rx');
    assert.equal(payload.quantity, 1);
    assert.deepEqual(payload.tags, ['жар', 'боль']);
});

test('serializeUpdateKitItem supports quantity and expiry updates', () => {
    const payload = serializeUpdateKitItem({ quantity: '3', expiry: '2029-05-01', isPrescription: false });
    assert.deepEqual(payload, {
        quantity: 3,
        expiry: '2029-05-01',
        status: 'otc',
    });
});

test('healthProfile serialize/deserialize roundtrip maps notes[] <-> special_notes', () => {
    const uiProfile = {
        age: 29,
        weight: 72.5,
        chronic: ['Гастрит'],
        allergies: ['Аспирин'],
        notes: ['Давление в норме', 'Принимать после еды'],
    };

    const apiPayload = serializeHealthProfile(uiProfile);
    assert.deepEqual(apiPayload, {
        age: 29,
        weight_kg: 72.5,
        chronic_diseases: ['Гастрит'],
        allergies: ['Аспирин'],
        special_notes: 'Давление в норме; Принимать после еды',
    });

    const restored = deserializeHealthProfile(apiPayload);
    assert.deepEqual(restored, uiProfile);
});

test('getApiBase returns /api/v1 outside browser window', () => {
    assert.equal(getApiBase(), '/api/v1');
});
