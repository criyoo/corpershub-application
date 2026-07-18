import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SearchableSelectDropdown } from "@/components/ui/searchable-select-dropdown";

describe("SearchableSelectDropdown", () => {
  it("filters options and selects the clicked value", () => {
    const handleChange = vi.fn();

    render(
      <SearchableSelectDropdown
        placeholder="Select your university"
        value=""
        groups={[
          {
            label: "Federal Universities",
            options: [
              { label: "University of Lagos", value: "University of Lagos" },
              { label: "University of Ibadan", value: "University of Ibadan" },
            ],
          },
          {
            label: "Private Universities",
            options: [{ label: "Babcock University Ilishan-Remo", value: "Babcock University Ilishan-Remo" }],
          },
        ]}
        onChange={handleChange}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /select your university/i }));
    fireEvent.change(screen.getByPlaceholderText("Type to search universities"), {
      target: { value: "lagos" },
    });

    const lagosOption = screen.getByRole("button", { name: /university of lagos/i });

    expect(lagosOption).toBeInTheDocument();
    expect(screen.queryByText("University of Ibadan")).not.toBeInTheDocument();
    expect(screen.queryByText("Babcock University Ilishan-Remo")).not.toBeInTheDocument();

    fireEvent.click(lagosOption);

    expect(handleChange).toHaveBeenCalledWith("University of Lagos");
  });
});
