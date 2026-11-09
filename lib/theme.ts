export type Theme='system'|'light'|'dark';
export function getTheme():Theme{const value=document.documentElement.dataset.theme;return value==='light'||value==='dark'?value:'system';}
export function applyTheme(theme:Theme){if(theme==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=theme;window.dispatchEvent(new Event('nexus-theme'));}
export function subscribeTheme(callback:()=>void){window.addEventListener('nexus-theme',callback);return()=>window.removeEventListener('nexus-theme',callback);}
