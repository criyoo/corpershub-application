"use client";

import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";

type DomainRule = {
  id: string;
  domain: string;
  rule_type: string;
};

type Option = {
  id: string;
  category: string;
  label: string;
  value: string;
};

export default function AdminConfigurationPage() {
  const domainRules = useApiQuery<{ results: DomainRule[] }>("/adminpanel/domain-rules/");
  const options = useApiQuery<{ results: Option[] }>("/adminpanel/options/");

  async function createDomainRule(formData: FormData) {
    try {
      await apiFetch("/adminpanel/domain-rules/", {
        method: "POST",
        body: JSON.stringify({
          domain: formData.get("domain"),
          rule_type: formData.get("rule_type"),
          note: ""
        })
      });
      toast.success("Domain rule created.");
      await domainRules.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to create domain rule.");
    }
  }

  async function createOption(formData: FormData) {
    try {
      await apiFetch("/adminpanel/options/", {
        method: "POST",
        body: JSON.stringify({
          category: formData.get("category"),
          label: formData.get("label"),
          value: formData.get("value")
        })
      });
      toast.success("Platform option created.");
      await options.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to create option.");
    }
  }

  return (
    <DashboardShell role="admin" title="Configuration">
      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <h2 className="font-display text-xl text-white">Company email domain rules</h2>
          <form action={createDomainRule} className="mt-4 grid gap-3 md:grid-cols-[1fr_180px_auto]">
            <Input name="domain" placeholder="example.com" required />
            <Select name="rule_type" defaultValue="allowlist">
              <option value="allowlist">Allowlist</option>
              <option value="denylist">Denylist</option>
            </Select>
            <Button type="submit">Add rule</Button>
          </form>
          <div className="mt-6 grid gap-2 text-sm text-mist">
            {domainRules.data?.results.map((rule) => (
              <div key={rule.id}>
                {rule.domain} · {rule.rule_type}
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <h2 className="font-display text-xl text-white">Catalog options</h2>
          <form action={createOption} className="mt-4 grid gap-3 md:grid-cols-2">
            <Select name="category" defaultValue="sector">
              <option value="sector">Sector</option>
              <option value="university">University</option>
              <option value="degree">Degree</option>
              <option value="posting_location">Posting location</option>
            </Select>
            <Input name="label" placeholder="Label" required />
            <Input name="value" placeholder="Value" required />
            <Button type="submit">Add option</Button>
          </form>
          <div className="mt-6 grid gap-2 text-sm text-mist">
            {options.data?.results.map((option) => (
              <div key={option.id}>
                {option.category} · {option.label} ({option.value})
              </div>
            ))}
          </div>
        </Card>
      </div>
    </DashboardShell>
  );
}
