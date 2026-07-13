import { PUBLIC_API_URL } from '$env/static/public';

export async function apiFetch<T>(
	fetch: typeof globalThis.fetch,
	path: string,
	options: RequestInit = {}
): Promise<T> {
	const response = await fetch(`${PUBLIC_API_URL}${path}`, {
		credentials: 'include',
		...options
	});

	if (!response.ok) {
		throw new Error(`API Error: ${response.status}`);
	}

	if (response.status === 204) {
		return undefined as T;
	}

	return response.json() as Promise<T>;
}
