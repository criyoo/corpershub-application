import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MultiSelectDropdown } from "@/components/ui/multi-select-dropdown";

describe("MultiSelectDropdown", () => {
  it("filters options as the user types in searchable mode", () => {
    const handleChange = vi.fn();

    render(
      <MultiSelectDropdown
        placeholder="Select field of study"
        values={[]}
        groups={[
          { label: "Management", options: ["Accounting", "Business Administration"] },
          { label: "Sciences", options: ["Computer Science", "Statistics"] },
        ]}
        searchable
        onChange={handleChange}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /select field of study/i }));
    fireEvent.change(screen.getByPlaceholderText("Type to filter options"), {
      target: { value: "computer" },
    });

    expect(screen.getByText("Computer Science")).toBeInTheDocument();
    expect(screen.queryByText("Accounting")).not.toBeInTheDocument();
    expect(screen.queryByText("Statistics")).not.toBeInTheDocument();
  });
});
