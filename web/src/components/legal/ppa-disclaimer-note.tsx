import Link from "next/link";

export function PpaDisclaimerNote({ className }: { className?: string }) {
  return (
    <p className={className ?? "text-xs leading-6 text-mist"}>
      corpershub does not assign PPAs, guarantee placements, interviews, allowances, workplace
      conditions, or NYSC outcomes.{" "}
      <Link href="/legal/ppa-placement-disclaimer" className="font-semibold text-lime hover:text-white">
        Read the full PPA Placement Disclaimer
      </Link>
      .
    </p>
  );
}
