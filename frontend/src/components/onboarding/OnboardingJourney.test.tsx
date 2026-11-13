import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OnboardingJourney } from "@/components/onboarding/OnboardingJourney";

describe("OnboardingJourney", () => {
  it("renders both tracks, the gate and the handoff", () => {
    render(
      <OnboardingJourney
        projectName="Ridgefield Weddings and Events"
        taskCount={194}
        listCount={2}
        onBack={vi.fn()}
        onRestart={vi.fn()}
      />,
    );
    expect(screen.getByText(/Ridgefield Weddings and Events approved/)).toBeInTheDocument();
    expect(screen.getByText("Ads track")).toBeInTheDocument();
    expect(screen.getByText("LeadLock track")).toBeInTheDocument();
    expect(screen.getByText("Cross-track launch")).toBeInTheDocument();
    expect(screen.getByText("Fully onboarded")).toBeInTheDocument();
    expect(screen.getByText(/Run the walkthrough again/)).toBeInTheDocument();
  });
});
