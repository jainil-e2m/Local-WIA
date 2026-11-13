import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2.5 whitespace-nowrap rounded-full text-sm font-bold uppercase tracking-[0.14em] ring-offset-background transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        /* Light-ground variants. Every hover used to resolve to white, which
           is invisible now the page is white -- each one darkens instead. */
        primary:
          "bg-brand-primary text-white border-2 border-brand-primary shadow-[0_12px_30px_-10px_rgba(80,112,255,0.45)] hover:bg-brand-accent hover:border-brand-accent hover:-translate-y-0.5",
        ghost:
          "bg-transparent text-brand-secondary border-2 border-brand-stone hover:bg-brand-secondary hover:text-white hover:border-brand-secondary hover:-translate-y-0.5",
        light:
          "bg-white text-brand-primary border-2 border-brand-mist hover:bg-brand-primary hover:border-brand-primary hover:text-white hover:-translate-y-0.5 shadow-[0_10px_30px_-14px_rgba(34,30,23,0.22)]",
        solid:
          "bg-brand-accent text-white border-2 border-brand-accent hover:bg-brand-secondary hover:border-brand-secondary shadow-[0_12px_26px_-14px_rgba(34,30,23,0.4)]",
        locked:
          "bg-brand-mist text-brand-gray border-2 border-brand-stone cursor-not-allowed",
      },
      size: {
        default: "h-12 px-8 py-3",
        sm: "h-11 px-6 text-[13px] tracking-[0.12em]",
        lg: "h-14 px-10",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
