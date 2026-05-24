// Configurable product name — set VITE_APP_NAME in your .env to override.
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'FinOps OS';
export const APP_INITIAL = (import.meta.env.VITE_APP_NAME || 'FinOps OS').charAt(0).toUpperCase();
