import { z } from 'zod';
export const credentials = z.object({ email: z.email(), password: z.string().min(12).max(128) });
export const profileInput = z.object({ username: z.string().regex(/^[a-z0-9_]{3,24}$/), display_name: z.string().trim().min(1).max(60), bio: z.string().trim().max(280) });
export const postInput = z.string().trim().min(1).max(2000);
export const commentInput = z.string().trim().min(1).max(500);
export const identifier = z.uuid();
