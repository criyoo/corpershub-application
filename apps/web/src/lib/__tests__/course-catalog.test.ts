import { describe, expect, it } from "vitest";

import {
  courseCatalogHasCourse,
  toCourseOptionGroups,
  type CourseCatalogField,
} from "@/lib/course-catalog";

const CATALOG_FIELDS: CourseCatalogField[] = [
  {
    id: "field-1",
    name: "University Courses",
    categories: [
      {
        id: "category-1",
        name: "Natural & Applied Sciences",
        courses: [
          { id: "course-1", name: "Computer Science" },
          { id: "course-2", name: "Statistics" },
        ],
      },
      {
        id: "category-2",
        name: "Management Sciences & Business",
        courses: [{ id: "course-3", name: "Accounting" }],
      },
    ],
  },
];

describe("courseCatalogHasCourse", () => {
  it("matches known courses after trimming whitespace", () => {
    expect(courseCatalogHasCourse(CATALOG_FIELDS, " Computer Science ")).toBe(true);
  });

  it("rejects courses outside the catalog", () => {
    expect(courseCatalogHasCourse(CATALOG_FIELDS, "Astrobiology")).toBe(false);
  });
});

describe("toCourseOptionGroups", () => {
  it("maps categories into option groups", () => {
    expect(toCourseOptionGroups(CATALOG_FIELDS)).toEqual([
      {
        label: "Natural & Applied Sciences",
        options: ["Computer Science", "Statistics"],
      },
      {
        label: "Management Sciences & Business",
        options: ["Accounting"],
      },
    ]);
  });

  it("preserves selected values that no longer exist in the catalog", () => {
    expect(toCourseOptionGroups(CATALOG_FIELDS, ["Fine Arts"])[0]).toEqual({
      label: "Other saved values",
      options: ["Fine Arts"],
    });
  });
});
