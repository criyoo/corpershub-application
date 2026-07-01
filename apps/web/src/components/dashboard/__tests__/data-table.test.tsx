import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataTable } from "@/components/dashboard/data-table";

describe("DataTable", () => {
  it("renders empty state when no rows are present", () => {
    render(
      <DataTable
        columns={["Name"]}
        rows={[]}
        emptyTitle="Nothing here"
        emptyDescription="Add records to populate this table."
      />
    );

    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("renders rows when data exists", () => {
    render(
      <DataTable
        columns={["Name", "Role"]}
        rows={[["Ada", "Corper"]]}
        emptyTitle="Nothing here"
        emptyDescription="Add records to populate this table."
      />
    );

    expect(screen.getByText("Ada")).toBeInTheDocument();
    expect(screen.getByText("Corper")).toBeInTheDocument();
  });
});
