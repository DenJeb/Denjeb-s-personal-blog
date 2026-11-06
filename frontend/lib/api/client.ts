import "server-only";

import createClient from "openapi-fetch";

import { env } from "../env";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: env.API_BASE_URL });
