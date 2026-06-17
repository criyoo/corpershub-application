export type CourseCatalogCourse = {
  id: string;
  name: string;
};

export type CourseCatalogCategory = {
  id: string;
  name: string;
  courses: CourseCatalogCourse[];
};

export type CourseCatalogField = {
  id: string;
  name: string;
  categories: CourseCatalogCategory[];
};

export type CourseCatalogResponse = {
  fields: CourseCatalogField[];
};

type OptionGroup = {
  label: string;
  options: string[];
};

function normalizeOptionList(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right)
  );
}

export function courseCatalogHasCourse(fields: CourseCatalogField[], value: string) {
  const normalizedValue = value.trim();
  if (!normalizedValue) {
    return false;
  }

  return fields.some((field) =>
    field.categories.some((category) =>
      category.courses.some((course) => course.name === normalizedValue)
    )
  );
}

export function toCourseOptionGroups(fields: CourseCatalogField[], extraOptions: string[] = []): OptionGroup[] {
  const baseGroups = fields.flatMap((field) =>
    field.categories.map((category) => ({
      label: fields.length > 1 ? `${field.name} · ${category.name}` : category.name,
      options: category.courses.map((course) => course.name),
    }))
  );
  const knownOptions = new Set(baseGroups.flatMap((group) => group.options));
  const orphanOptions = normalizeOptionList(extraOptions).filter((option) => !knownOptions.has(option));

  return orphanOptions.length > 0
    ? [{ label: "Other saved values", options: orphanOptions }, ...baseGroups]
    : baseGroups;
}
