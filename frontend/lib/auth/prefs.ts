import { z } from "zod";

// User preference shape synced from v2.0 (a11y/theme). strictObject: unknown keys are rejected
// so a malicious client can't smuggle extra columns into the prefs JSONB.
export const prefsSchema = z.strictObject({
  theme: z.enum(["light", "dark", "system"]).default("system"),
  reducedMotion: z.boolean().default(false),
  accent: z
    .string()
    .regex(/^[a-z0-9-]+$/)
    .optional(),
});

export type Prefs = z.infer<typeof prefsSchema>;

export function parsePrefs(input: unknown): Prefs {
  return prefsSchema.parse(input ?? {});
}
