// Build-time branding; use frontend/.env.local for your own installation.
export const site = {
  name: import.meta.env.VITE_SITE_NAME || 'RuCorpus',
  subtitle: import.meta.env.VITE_SITE_SUBTITLE || 'Parallel Corpus Search System',
}
