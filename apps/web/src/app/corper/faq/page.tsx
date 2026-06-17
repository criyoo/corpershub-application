import { SupportFaqPage } from "@/components/support/support-page";
import { loadSupportFaqItems } from "@/lib/support-faq";

export default async function CorperFaqPage() {
  const faqItems = await loadSupportFaqItems("corper");
  return <SupportFaqPage role="corper" faqItems={faqItems} />;
}
