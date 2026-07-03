export function buildCompanyCorperDetailPath(corperId: string) {
  return `/company/corpers?corperId=${encodeURIComponent(corperId)}`;
}

export function buildCorperCompanyDetailPath(companyId: string) {
  return `/corper/companies?companyId=${encodeURIComponent(companyId)}`;
}

export function buildCompanyChatPath(conversationId: string) {
  return `/company/chat?conversationId=${encodeURIComponent(conversationId)}`;
}

export function buildCorperChatPath(conversationId: string) {
  return `/corper/chat?conversationId=${encodeURIComponent(conversationId)}`;
}
