declare const process: {
  env: Record<string, string | undefined>;
};

declare module "clsx" {
  export default function clsx(...inputs: Array<unknown>): string;
}

declare module "sonner" {
  type ToastOptions = {
    duration?: number;
    [key: string]: unknown;
  };

  export const toast: {
    success(message: string, options?: ToastOptions): void;
    error(message: string, options?: ToastOptions): void;
  };

  export function Toaster(props: {
    richColors?: boolean;
    position?: string;
    [key: string]: unknown;
  }): React.ReactElement | null;
}

declare module "tailwindcss" {
  export interface Config {
    [key: string]: any;
  }
}

declare module "vitest/config" {
  export function defineConfig(config: Record<string, unknown>): Record<string, unknown>;
}

declare module "vitest" {
  export const describe: (...args: any[]) => any;
  export interface ExpectStatic {
    (...args: any[]): any;
    objectContaining(...args: any[]): any;
  }
  export const expect: ExpectStatic;
  export const it: (...args: any[]) => any;
  export const beforeEach: (...args: any[]) => any;
  export const afterEach: (...args: any[]) => any;
  export const vi: Record<string, any>;
}

declare module "next" {
  export type Metadata = Record<string, unknown>;
}

declare module "next/link" {
  export default function Link(props: {
    href: string;
    children?: React.ReactNode;
    [key: string]: unknown;
  }): React.ReactElement | null;
}

declare module "next/image" {
  export default function Image(props: {
    src: string;
    alt: string;
    children?: React.ReactNode;
    [key: string]: unknown;
  }): React.ReactElement | null;
}

declare module "next/navigation" {
  export function redirect(path: string): never;
  export function usePathname(): string;
  export function useRouter(): {
    push(path: string): void;
    replace(path: string): void;
    back(): void;
    prefetch(path: string): Promise<void>;
  };
  export function useSearchParams(): {
    get(name: string): string | null;
  };
}

declare module "next/font/google" {
  export function Open_Sans(options?: Record<string, unknown>): {
    className: string;
    variable: string;
    style: Record<string, unknown>;
  };
}

declare module "@testing-library/react" {
  export const render: (...args: any[]) => any;
  export const screen: Record<string, any>;
  export const fireEvent: Record<string, any>;
  export const waitFor: (...args: any[]) => any;
}
