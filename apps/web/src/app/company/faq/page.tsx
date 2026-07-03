import { SupportFaqPage } from "@/components/support/support-page";
import { loadSupportFaqItems } from "@/lib/support-faq";

export default async function CompanyFaqPage() {
  const faqItems = await loadSupportFaqItems("company");
  return <SupportFaqPage role="company" faqItems={faqItems} />;
}
