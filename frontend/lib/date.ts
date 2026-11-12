/**
 * API 返回的是站点本地时间（不带时区偏移），直接按字符串展示，
 * 避免浏览器按访问者时区再次换算。
 */
export function formatDateTime(value: string): string {
  const [date, time = ""] = value.split("T");
  return time ? `${date} ${time.slice(0, 5)}` : date;
}
