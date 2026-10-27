/** cn — merge Tailwind classes safely (tailwind-merge + clsx). */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Tiny body-scroll lock helper for dialogs/drawers. */
export function lockBodyScroll(lock: boolean): void {
  if (typeof document === "undefined") return;
  document.body.style.overflow = lock ? "hidden" : "";
}

/** Format a number as a currency-free byte count for display. */
export function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
