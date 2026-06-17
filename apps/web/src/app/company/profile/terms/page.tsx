import { LegalAgreementPage } from "@/components/legal/legal-agreement-page";
import { getCompanyLegalDocuments } from "@/lib/legal-documents";

export default async function CompanyProfileTermsPage() {
  const documents = await getCompanyLegalDocuments();
  return <LegalAgreementPage role="company" documents={documents} />;
}
