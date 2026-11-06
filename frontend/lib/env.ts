import "server-only";

import { z } from "zod";

const schema = z.object({
  API_BASE_URL: z.string().url(),
  NEXT_PUBLIC_SITE_URL: z.string().url(),
});

export type Env = z.infer<typeof schema>;
export type EnvInput = Record<string, string | undefined>;

export function parseEnv(input: EnvInput): Env {
  return schema.parse(input);
}

export const env = parseEnv(process.env);
