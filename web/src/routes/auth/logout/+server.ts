import { redirect } from '@sveltejs/kit';

import { logout } from '$lib/api/auth';

export async function GET({ fetch }) {
	await logout(fetch);

	throw redirect(303, '/');
}
