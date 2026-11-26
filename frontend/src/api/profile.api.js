import { request } from './client.js';

/**
 * Преобразует объект медкарты из UI-формата в UpdateHealthProfileRequest (extra="forbid").
 */
export function serializeHealthProfile(profile) {
    const p = profile || {};
    const ageNum = p.age !== undefined && p.age !== null && p.age !== '' ? Number.parseInt(p.age, 10) : null;
    const weightNum = p.weight_kg !== undefined
        ? Number.parseFloat(p.weight_kg)
        : (p.weight !== undefined && p.weight !== null && p.weight !== '' ? Number.parseFloat(p.weight) : null);

    const chronic = Array.isArray(p.chronic_diseases)
        ? p.chronic_diseases
        : (Array.isArray(p.chronic) ? p.chronic : []);
    const allergies = Array.isArray(p.allergies) ? p.allergies : [];
    let notesText = null;
    if (typeof p.special_notes === 'string') {
        notesText = p.special_notes.trim() || null;
    } else if (Array.isArray(p.notes) && p.notes.length > 0) {
        notesText = p.notes.map((n) => String(n).trim()).filter(Boolean).join('; ') || null;
    }

    const payload = {
        chronic_diseases: chronic.map((c) => String(c).trim()).filter(Boolean),
        allergies: allergies.map((a) => String(a).trim()).filter(Boolean),
        special_notes: notesText,
    };
    if (Number.isFinite(ageNum) && ageNum >= 0 && ageNum <= 130) payload.age = ageNum;
    if (Number.isFinite(weightNum) && weightNum >= 1 && weightNum <= 300) payload.weight_kg = weightNum;
    return payload;
}

/**
 * Преобразует ответ GET/PUT /api/v1/profile во внутренний формат UI медкарты.
 */
export function deserializeHealthProfile(apiProfile) {
    if (!apiProfile || apiProfile._fallback || apiProfile._status >= 400) return null;
    const rawNotes = typeof apiProfile.special_notes === 'string' ? apiProfile.special_notes : '';
    const notes = rawNotes
        .split(';')
        .map((s) => s.trim())
        .filter(Boolean);
    return {
        age: apiProfile.age ?? 25,
        weight: apiProfile.weight_kg ?? 65,
        chronic: Array.isArray(apiProfile.chronic_diseases) ? apiProfile.chronic_diseases : [],
        allergies: Array.isArray(apiProfile.allergies) ? apiProfile.allergies : [],
        notes,
    };
}

export const profileApi = {
    async getProfile() {
        const res = await request('/profile');
        return deserializeHealthProfile(res);
    },

    async updateProfile(profile) {
        const payload = serializeHealthProfile(profile);
        const res = await request('/profile', {
            method: 'PUT',
            body: JSON.stringify(payload),
        });
        if (res._fallback || res._status >= 400) return res;
        return deserializeHealthProfile(res);
    },
};
