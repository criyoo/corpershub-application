declare module "lucide-react" {
  import type { FC, SVGProps } from "react";

  export type LucideProps = SVGProps<SVGSVGElement> & {
    size?: string | number;
    absoluteStrokeWidth?: boolean;
  };

  export const ArrowRight: FC<LucideProps>;
  export const ArrowLeft: FC<LucideProps>;
  export const CheckCircle2: FC<LucideProps>;
  export const CircleHelp: FC<LucideProps>;
  export const CircleAlert: FC<LucideProps>;
  export const Clock3: FC<LucideProps>;
  export const FileText: FC<LucideProps>;
  export const Fingerprint: FC<LucideProps>;
  export const Eye: FC<LucideProps>;
  export const EyeOff: FC<LucideProps>;
  export const Lightbulb: FC<LucideProps>;
  export const Mail: FC<LucideProps>;
  export const MessageSquare: FC<LucideProps>;
  export const PhoneCall: FC<LucideProps>;
  export const ShieldCheck: FC<LucideProps>;
  export const Sparkles: FC<LucideProps>;
  export const Upload: FC<LucideProps>;
  export const X: FC<LucideProps>;
}
