function toSortedUniqueList(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right)
  );
}

export const NIGERIAN_STATES = [
  "Abia",
  "Adamawa",
  "Akwa Ibom",
  "Anambra",
  "Bauchi",
  "Bayelsa",
  "Benue",
  "Borno",
  "Cross River",
  "Delta",
  "Ebonyi",
  "Edo",
  "Ekiti",
  "Enugu",
  "Federal Capital Territory",
  "Gombe",
  "Imo",
  "Jigawa",
  "Kaduna",
  "Kano",
  "Katsina",
  "Kebbi",
  "Kogi",
  "Kwara",
  "Lagos",
  "Nasarawa",
  "Niger",
  "Ogun",
  "Ondo",
  "Osun",
  "Oyo",
  "Plateau",
  "Rivers",
  "Sokoto",
  "Taraba",
  "Yobe",
  "Zamfara",
] as const;

export function getNigerianStateSlug(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function getNigerianStateBySlug(slug: string) {
  return NIGERIAN_STATES.find((state) => getNigerianStateSlug(state) === slug);
}

export const CORPER_GENDERS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
] as const;

export const CORPER_BATCHES = [
  { value: "Batch A", label: "Batch A" },
  { value: "Batch B", label: "Batch B" },
  { value: "Batch C", label: "Batch C" },
] as const;

export const CORPER_STREAMS = [
  { value: "Stream 1", label: "Stream 1" },
  { value: "Stream 2", label: "Stream 2" },
] as const;

const POLYTECHNIC_QUALIFICATIONS = toSortedUniqueList([
  "ND",
  "HND",
]);

const BACHELOR_DEGREES = toSortedUniqueList([
  "B.Sc",
  "B.A",
  "B.Eng",
  "B.Tech",
  "LLB (Law)",
  "MBBS",
  "B.Pharm",
  "DVM",
  "BNSc.",
  "B.Ed",
  "B.HLIS",
]);

const POSTGRADUATE_DEGREES = toSortedUniqueList([
  "PGD",
  "M.Sc.",
  "M.A.",
  "M.Eng.",
  "M.Phil",
  "PhD",
]);

export const NIGERIAN_DEGREE_GROUPS = [
  { label: "Polytechnic", degrees: POLYTECHNIC_QUALIFICATIONS },
  { label: "Bachelor's", degrees: BACHELOR_DEGREES },
  { label: "Post-graduate Degree", degrees: POSTGRADUATE_DEGREES },
] as const;

export const NIGERIAN_TERTIARY_SUBJECT_GROUPS = [
  {
    label: "Agriculture",
    subjects: toSortedUniqueList([
      "Agricultural Economics",
      "Agricultural Extension",
      "Agronomy",
      "Animal Science",
      "Crop Science",
      "Fisheries",
      "Food Science and Technology",
      "Forestry",
      "Soil Science",
    ]),
  },
  {
    label: "Arts and Humanities",
    subjects: toSortedUniqueList([
      "Arabic",
      "Christian Religious Studies",
      "English and Literary Studies",
      "Fine and Applied Arts",
      "French",
      "History and International Studies",
      "Islamic Studies",
      "Languages and Linguistics",
      "Music",
      "Philosophy",
      "Theatre Arts",
    ]),
  },
  {
    label: "Education",
    subjects: toSortedUniqueList([
      "Adult Education",
      "Business Education",
      "Early Childhood Education",
      "Educational Administration",
      "Guidance and Counselling",
      "Library and Information Science",
      "Physical and Health Education",
      "Science Education",
      "Technical Education",
    ]),
  },
  {
    label: "Engineering and Technology",
    subjects: toSortedUniqueList([
      "Agricultural Engineering",
      "Chemical Engineering",
      "Civil Engineering",
      "Computer Engineering",
      "Electrical and Electronics Engineering",
      "Industrial Engineering",
      "Mechanical Engineering",
      "Mechatronics Engineering",
      "Metallurgical and Materials Engineering",
      "Petroleum Engineering",
    ]),
  },
  {
    label: "Environmental Sciences",
    subjects: toSortedUniqueList([
      "Architecture",
      "Building",
      "Estate Management",
      "Quantity Surveying",
      "Surveying and Geoinformatics",
      "Urban and Regional Planning",
    ]),
  },
  {
    label: "Health Sciences",
    subjects: toSortedUniqueList([
      "Anatomy",
      "Dentistry",
      "Medical Laboratory Science",
      "Medicine and Surgery",
      "Nursing Science",
      "Optometry",
      "Pharmacy",
      "Physiology",
      "Physiotherapy",
      "Public Health",
      "Radiography",
      "Veterinary Medicine",
    ]),
  },
  {
    label: "Law",
    subjects: toSortedUniqueList(["Law"]),
  },
  {
    label: "Management and Social Sciences",
    subjects: toSortedUniqueList([
      "Accounting",
      "Actuarial Science",
      "Banking and Finance",
      "Business Administration",
      "Economics",
      "Entrepreneurship",
      "Human Resource Management",
      "Industrial Relations",
      "Insurance",
      "International Relations",
      "Mass Communication",
      "Marketing",
      "Political Science",
      "Project Management",
      "Public Administration",
      "Sociology",
    ]),
  },
  {
    label: "Pure and Applied Sciences",
    subjects: toSortedUniqueList([
      "Biochemistry",
      "Biology",
      "Biotechnology",
      "Botany",
      "Chemistry",
      "Computer Science",
      "Cyber Security",
      "Data Science",
      "Environmental Science",
      "Geology",
      "Industrial Chemistry",
      "Mathematics",
      "Microbiology",
      "Physics",
      "Statistics",
      "Zoology",
    ]),
  },
] as const;

const NIGERIAN_DEGREES = new Set(NIGERIAN_DEGREE_GROUPS.flatMap((group) => group.degrees));

export function isKnownNigerianDegree(value: string) {
  return NIGERIAN_DEGREES.has(value.trim());
}
