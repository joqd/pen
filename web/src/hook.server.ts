import type { Handle } from '@sveltejs/kit';

import { me } from '$lib/api/auth';

export const handle: Handle = async ({ event, resolve }) => {
	try {
		event.locals.user = await me(event.fetch);
	} catch {
		event.locals.user = null;
	}

	return resolve(event);
};
