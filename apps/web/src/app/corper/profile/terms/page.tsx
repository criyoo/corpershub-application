import { LegalAgreementPage } from "@/components/legal/legal-agreement-page";
import { getCorperLegalDocuments } from "@/lib/legal-documents";

export default async function CorperProfileTermsPage() {
  const documents = await getCorperLegalDocuments();
  return <LegalAgreementPage role="corper" documents={documents} />;
}
