import { apiFetch } from './client';

export interface User {
	id: number;
	phone: string;
}

export interface LoginData {
	phone: string;
}

export interface VerifyOTPData {
	phone: string;
	code: number;
}

export async function login(fetch: typeof globalThis.fetch, data: LoginData) {
	return apiFetch(fetch, '/auth/login/', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(data)
	});
}

export async function verifyOTP(fetch: typeof globalThis.fetch, data: VerifyOTPData) {
	return apiFetch(fetch, '/auth/verify/', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(data)
	});
}

export async function logout(fetch: typeof globalThis.fetch) {
	return apiFetch(fetch, '/auth/logout/', {
		method: 'POST'
	});
}

export async function me(fetch: typeof globalThis.fetch): Promise<User> {
	return apiFetch(fetch, '/auth/me/');
}
