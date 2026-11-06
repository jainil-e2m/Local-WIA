import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3.5 py-1.5 text-[11.5px] font-bold uppercase tracking-[0.12em] leading-none transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-brand-primary text-white",
        outline: "border-brand-lavender/50 text-brand-secondary",
        live: "border-brand-teal/45 bg-brand-teal/15 text-[#1f7a6c]",
        dev: "border-brand-orange/45 bg-brand-orange/15 text-[#a5641a]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
