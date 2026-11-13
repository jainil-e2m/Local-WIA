import { forwardRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ATELIER_UNAVAILABLE, atelierLaunchHref } from "@/lib/atelierLaunch";
import type { V1Action } from "./destinations";
import { useV1Action } from "./useV1Action";

interface ActionLinkProps {
  action: V1Action;
  className?: string;
  children: ReactNode;
  "aria-label"?: string;
  onFocus?: () => void;
  onBlur?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  /** Runs before the action — e.g. closing the menu the link sits in. */
  onBeforeAction?: () => void;
  tabIndex?: number;
}

/**
 * The right element for each kind of destination: a router Link for an
 * in-app route and a real anchor for an external one, so both can be
 * middle-clicked or opened in a new tab; a same-tab anchor for the Content
 * Atelier's launch link (a server route), disabled where it is not
 * configured; a button for the actions that open something on this page.
 */
export const ActionLink = forwardRef<HTMLElement, ActionLinkProps>(function ActionLink(
  { action, className, children, onBeforeAction, ...rest },
  ref,
) {
  const run = useV1Action();

  if (action.kind === "route") {
    return (
      <Link
        ref={ref as React.Ref<HTMLAnchorElement>}
        to={action.to}
        className={className}
        onClick={onBeforeAction}
        {...rest}
      >
        {children}
      </Link>
    );
  }

  if (action.kind === "external") {
    return (
      <a
        ref={ref as React.Ref<HTMLAnchorElement>}
        href={action.href}
        target="_blank"
        rel="noopener noreferrer"
        className={className}
        onClick={onBeforeAction}
        {...rest}
      >
        {children}
      </a>
    );
  }

  if (action.kind === "atelier") {
    const href = atelierLaunchHref();
    return href ? (
      <a
        ref={ref as React.Ref<HTMLAnchorElement>}
        href={href}
        className={className}
        onClick={onBeforeAction}
        {...rest}
      >
        {children}
      </a>
    ) : (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        type="button"
        disabled
        title={ATELIER_UNAVAILABLE}
        className={className}
        {...rest}
      >
        {children}
      </button>
    );
  }

  return (
    <button
      ref={ref as React.Ref<HTMLButtonElement>}
      type="button"
      className={className}
      onClick={() => {
        onBeforeAction?.();
        run(action);
      }}
      {...rest}
    >
      {children}
    </button>
  );
});
