"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { DataTable } from "@/components/dashboard/data-table";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";

type Payment = {
  id: string;
  reference: string;
  tx_ref: string;
  gateway: string;
  flutterwave_transaction_id: string;
  status: string;
  amount_kobo: number;
  customer_email: string;
  plan_name: string;
  verified_at: string | null;
  created_at: string;
};

type SettlementAccount = {
  provider: string;
  configured: boolean;
  bank_name: string;
  account_number: string;
  account_number_masked: string;
  dashboard_configuration_required: boolean;
};

export default function AdminPaymentsPage() {
  const payments = useApiQuery<{ results: Payment[] }>("/payments/admin/transactions/");
  const settlementAccount = useApiQuery<SettlementAccount>("/payments/admin/settlement-account/");

  return (
    <DashboardShell role="admin" title="Payments">
      <div className="grid gap-6">
        <Card className="grid gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Payment settlement</p>
            <h2 className="mt-2 font-display text-2xl text-white">
              {settlementAccount.data?.configured ? "Settlement account configured" : "Settlement account pending"}
            </h2>
          </div>
          <p className="text-sm text-mist">
            Bank: {settlementAccount.data?.bank_name || "Not set"}
          </p>
          <p className="text-sm text-mist">
            Account number: {settlementAccount.data?.account_number || "Not set"}
          </p>
          <p className="text-sm text-mist">
            The Payment provider still requires the same settlement account to be selected in Dashboard Settings {">"} Business preferences.
          </p>
        </Card>

        <DataTable
          columns={["Payment ID", "Tx Ref", "FLW Tx ID", "Status", "Amount", "Customer", "Verified", "Created"]}
          rows={
            payments.data?.results.map((payment) => [
              payment.id,
              payment.tx_ref || payment.reference,
              payment.flutterwave_transaction_id || "Pending",
              payment.status,
              `₦${(payment.amount_kobo / 100).toLocaleString()}`,
              payment.customer_email,
              payment.verified_at ? new Date(payment.verified_at).toLocaleString() : "Not yet",
              new Date(payment.created_at).toLocaleString()
            ]) ?? []
          }
          loading={payments.loading}
          emptyTitle="No payments"
          emptyDescription="Payment transactions will appear here."
        />
      </div>
    </DashboardShell>
  );
}
