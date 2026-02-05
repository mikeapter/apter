import * as React from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

function cx(...parts: Array<string | undefined | false>) {
  return parts.filter(Boolean).join(" ");
}

/**
 * Institutional Button
 * - No hover effects
 * - No transitions
 * - Deliberate pressed feedback only (opacity)
 * - Focus-visible outline for accessibility
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", disabled, ...props }, ref) => {
    const base =
      "institutional-interactive inline-flex items-center justify-center rounded-md " +
      "border px-3 py-2 text-sm font-medium " +
      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 " +
      "disabled:opacity-50 disabled:cursor-not-allowed";

    const sizes: Record<ButtonSize, string> = {
      sm: "h-8 px-2 text-xs",
      md: "h-9 px-3 text-sm",
      lg: "h-10 px-4 text-sm",
    };

    const variants: Record<ButtonVariant, string> = {
      primary:
        "bg-[rgba(255,255,255,0.10)] border-[rgba(255,255,255,0.16)] text-white",
      secondary:
        "bg-transparent border-[rgba(255,255,255,0.16)] text-white",
      ghost:
        "bg-transparent border-transparent text-white underline underline-offset-4",
      danger:
        "bg-[rgba(255,255,255,0.10)] border-[rgba(255,255,255,0.16)] text-white",
    };

    // Deliberate click feedback: only active opacity shift (handled by globals.css)
    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cx(base, sizes[size], variants[variant], className)}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";
