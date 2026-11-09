'use client';
import {useSyncExternalStore} from 'react';
import {applyTheme,getTheme,subscribeTheme,type Theme} from '@/lib/theme';
export function Appearance(){const theme=useSyncExternalStore(subscribeTheme,getTheme,()=> 'system');
 function change(next:Theme){applyTheme(next);try{localStorage.setItem('nexus-theme',next);}catch{/* Theme works for the current page even without local storage. */}}
 return <section className="card stack"><h2>Your view</h2><label>Appearance<select value={theme} onChange={e=>change(e.target.value as Theme)}><option value="system">Use system setting</option><option value="light">Light</option><option value="dark">Dark</option></select></label><small>Saved in this browser. Your content and feed preferences remain unchanged.</small></section>;
}
