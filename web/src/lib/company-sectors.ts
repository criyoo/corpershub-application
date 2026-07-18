const COMPANY_SECTOR_NAMES = [
  "Advertising & Marketing",
  "Agriculture",
  "Arts & Culture",
  "Automotive",
  "Banking",
  "Beauty & Personal Care",
  "Creative Economy",
  "Defence Industry",
  "E-commerce",
  "Education",
  "Energy & Utilities",
  "Entertainment",
  "Environmental Services",
  "Event Management",
  "Financial Services",
  "Food Services",
  "Furniture & Wood Products",
  "Government Institution",
  "Healthcare & Pharmaceuticals",
  "Hospitality",
  "Household Services",
  "Technology & ICT",
  "Insurance",
  "Legal & Compliance",
  "Logistics & Supply Chain",
  "Manufacturing & Production",
  "Maritime",
  "Media & Communications",
  "NGO & Non-Profit",
  "Oil & Gas",
  "Outsourcing",
  "Professional Services",
  "Public Administration",
  "Publishing & Printing",
  "Real Estate & Construction",
  "Religious Institutions",
  "Research & Development",
  "Science",
  "Security & Investigation",
  "Social Work & Community Services",
  "Solid Minerals & Mining",
  "Sports & Recreation",
  "Telecommunications",
  "Textile & Garment",
  "Tourism",
  "Trade (Wholesale & Retail)",
  "Transport & Aviation",
  "Waste Management"
] as const;

export type CompanySectorName = (typeof COMPANY_SECTOR_NAMES)[number];

export const COMPANY_SECTOR_OPTIONS: string[] = [...COMPANY_SECTOR_NAMES];

export function getCompanySectorSlug(name: string) {
  return name
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const COMPANY_SECTOR_IMAGE_BY_NAME: Record<CompanySectorName, string> = {
  "Advertising & Marketing": "/images/company-sectors/advertising-and-marketing.webp",
  "Agriculture": "/images/company-sectors/agriculture.webp",
  "Arts & Culture": "/images/company-sectors/arts-and-culture.webp",
  "Automotive": "/images/company-sectors/automotive.webp",
  "Banking": "/images/company-sectors/finance.webp",
  "Beauty & Personal Care": "/images/company-sectors/beauty-and-personal-care.webp",
  "Creative Economy": "/images/company-sectors/creative-economy.webp",
  "Defence Industry": "/images/company-sectors/defence-industry.webp",
  "E-commerce": "/images/company-sectors/e-commerce.webp",
  "Education": "/images/company-sectors/education.webp",
  "Energy & Utilities": "/images/company-sectors/energy.webp",
  "Entertainment": "/images/company-sectors/entertainment.webp",
  "Environmental Services": "/images/company-sectors/environmental-services.webp",
  "Event Management": "/images/company-sectors/event-management.webp",
  "Financial Services": "/images/company-sectors/financial-services.webp",
  "Food Services": "/images/company-sectors/food-services.webp",
  "Furniture & Wood Products": "/images/company-sectors/furniture-and-wood-products.webp",
  "Government Institution": "/images/company-sectors/government.webp",
  "Healthcare & Pharmaceuticals": "/images/company-sectors/healthcare.webp",
  "Hospitality": "/images/company-sectors/hospitality.webp",
  "Household Services": "/images/company-sectors/household-services.webp",
  "Technology & ICT": "/images/company-sectors/ict.webp",
  "Insurance": "/images/company-sectors/insurance.webp",
  "Legal & Compliance": "/images/company-sectors/legal.webp",
  "Logistics & Supply Chain": "/images/company-sectors/logistics.webp",
  "Manufacturing & Production": "/images/company-sectors/manufacturing.webp",
  "Maritime": "/images/company-sectors/maritime.webp",
  "Media & Communications": "/images/company-sectors/media.webp",
  "NGO & Non-Profit": "/images/company-sectors/ngo-non-profit.webp",
  "Oil & Gas": "/images/company-sectors/oil-and-gas.webp",
  "Outsourcing": "/images/company-sectors/outsourcing.webp",
  "Professional Services": "/images/company-sectors/professional-services.webp",
  "Public Administration": "/images/company-sectors/public-administration.webp",
  "Publishing & Printing": "/images/company-sectors/publishing-and-printing.webp",
  "Real Estate & Construction": "/images/company-sectors/real-estate-construction.webp",
  "Religious Institutions": "/images/company-sectors/religious-institution.webp",
  "Research & Development": "/images/company-sectors/research.webp",
  "Science": "/images/company-sectors/sciences.webp",
  "Security & Investigation": "/images/company-sectors/security.webp",
  "Social Work & Community Services": "/images/company-sectors/social-works.webp",
  "Solid Minerals & Mining": "/images/company-sectors/solid-minerals-and-mining.webp",
  "Sports & Recreation": "/images/company-sectors/sports-and-recreation.webp",
  // "Technology": "/images/company-sectors/technology.webp",
  "Telecommunications": "/images/company-sectors/telecommunications.webp",
  "Textile & Garment": "/images/company-sectors/textile-and-garment.webp",
  "Tourism": "/images/company-sectors/tourism.webp",
  "Trade (Wholesale & Retail)": "/images/company-sectors/trade.webp",
  "Transport & Aviation": "/images/company-sectors/transportation.webp",
  "Waste Management": "/images/company-sectors/waste-management.webp",
};

export const COMPANY_SECTORS = COMPANY_SECTOR_NAMES.map((name) => ({
  name,
  slug: getCompanySectorSlug(name),
  imageSrc: COMPANY_SECTOR_IMAGE_BY_NAME[name],
}));

export function getCompanySectorBySlug(slug: string) {
  return COMPANY_SECTORS.find((sector) => sector.slug === slug);
}
