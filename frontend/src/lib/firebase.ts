import { getApp, getApps, initializeApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';

const firebaseConfig = {
	apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
	authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
	projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
	appId: import.meta.env.VITE_FIREBASE_APP_ID
};

export const firebaseConfigured = Object.values(firebaseConfig).every(Boolean);

export const firebaseAuth: Auth | null = firebaseConfigured && typeof window !== 'undefined'
	? getAuth(
			getApps().length > 0
				? getApp()
				: initializeApp(firebaseConfig)
		)
	: null;
