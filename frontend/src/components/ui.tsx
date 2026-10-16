import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import { cn } from "../lib/utils";

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-teal text-white hover:bg-[#0c5c59]",
    secondary: "bg-white text-navy border border-line hover:bg-paper",
    ghost: "bg-transparent text-navy hover:bg-white",
    danger: "bg-white text-rose border border-rose/40 hover:bg-rose-soft",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
}

export function TextField({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink placeholder:text-muted",
        className,
      )}
      {...props}
    />
  );
}

export function TextArea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn("w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink", className)}
      {...props}
    />
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn("rounded-lg border border-line bg-card p-5 shadow-sm", className)}>{children}</section>;
}

export function Banner({ tone = "info", children }: { tone?: "info" | "warn" | "error"; children: ReactNode }) {
  const styles = {
    info: "bg-teal-soft text-navy border-teal/20",
    warn: "bg-amber-soft text-amber border-amber/20",
    error: "bg-rose-soft text-rose border-rose/20",
  };
  return (
    <div role="status" className={cn("rounded-md border px-3 py-2 text-sm", styles[tone])}>
      {children}
    </div>
  );
}
