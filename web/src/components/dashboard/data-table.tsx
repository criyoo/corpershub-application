import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

export function DataTable({
  columns,
  rows,
  loading,
  emptyTitle,
  emptyDescription
}: {
  columns: string[];
  rows: React.ReactNode[][];
  loading?: boolean;
  emptyTitle: string;
  emptyDescription: string;
}) {
  if (loading) {
    return (
      <Card className="grid gap-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </Card>
    );
  }

  if (!rows.length) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <Card className="overflow-x-auto p-0">
      <table className="min-w-full text-left text-sm text-white">
        <thead className="border-b border-line text-mist">
          <tr>
            {columns.map((column) => (
              <th key={column} className="px-4 py-4 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-b border-line/70 last:border-0">
              {row.map((cell, cellIndex) => (
                <td key={`${index}-${cellIndex}`} className="px-4 py-4 align-top text-mist">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
