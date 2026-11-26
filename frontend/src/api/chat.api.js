import { request } from './client.js';
import { serializeHealthProfile } from './profile.api.js';

export const chatApi = {
    async sendQuery(query, context = {}) {
        const healthProfile = context.health_profile
            ? serializeHealthProfile(context.health_profile)
            : null;
        return request('/chat/query', {
            method: 'POST',
            body: JSON.stringify({
                query,
                include_kit_context: context.include_kit_context ?? true,
                user_kit_names: context.user_kit_names || [],
                selected_pills: context.selected_pills || [],
                health_profile: healthProfile,
                response_depth: context.response_depth || 'detailed',
            }),
        });
    },
};
