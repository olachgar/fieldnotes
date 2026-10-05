import { firebaseAuth } from './firebase';

export type Note = {
	id: string;
	name: string;
	date: string;
	subject: string;
};

export type NoteInput = Pick<Note, 'name' | 'subject'>;

const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const user = firebaseAuth?.currentUser;
	if (!user) throw new Error('Sign in to access your notes.');
	const idToken = await user.getIdToken();
	const response = await fetch(`${apiBase}${path}`, {
		...init,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${idToken}`,
			...init?.headers
		}
	});
	if (response.status === 204) return undefined as T;

	const payload: unknown = await response.json().catch(() => null);
	if (!response.ok) {
		const detail =
			typeof payload === 'object' && payload !== null && 'detail' in payload
				? String(payload.detail)
				: `Request failed (${response.status})`;
		throw new Error(detail);
	}
	return payload as T;
}

export function listNotes(): Promise<Note[]> {
	return request<Note[]>('/api/notes');
}

export function createNote(input: NoteInput): Promise<Note> {
	return request<Note>('/api/notes', { method: 'POST', body: JSON.stringify(input) });
}

export function updateNote(id: string, input: NoteInput): Promise<Note> {
	return request<Note>(`/api/notes/${encodeURIComponent(id)}`, {
		method: 'PUT',
		body: JSON.stringify(input)
	});
}

export function deleteNote(id: string): Promise<void> {
	return request<void>(`/api/notes/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
