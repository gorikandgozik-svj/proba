'use client';
import {useEffect} from 'react';
import {applyTheme} from '@/lib/theme';
export function ThemeProvider(){useEffect(()=>{function load(){try{const saved=localStorage.getItem('nexus-theme');applyTheme(saved==='light'||saved==='dark'?saved:'system');}catch{/* Default to the system theme. */}}load();window.addEventListener('storage',load);return()=>window.removeEventListener('storage',load);},[]);return null;}
