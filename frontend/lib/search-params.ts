/**
 * Next.js 的 searchParams 值在重复参数时可能是 string[]，
 * 统一取第一个值，避免调用 .trim() / .startsWith() 时抛错。
 */
export function firstParam(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
