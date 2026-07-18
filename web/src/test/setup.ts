import "@testing-library/jest-dom";
import { createElement } from "react";
import { vi } from "vitest";

const MockLucideIcon = (props: Record<string, unknown>) => createElement("svg", props);

vi.mock("lucide-react", () => ({
  ArrowLeft: MockLucideIcon,
  Building2: MockLucideIcon,
  Eye: MockLucideIcon,
  EyeOff: MockLucideIcon,
  Lock: MockLucideIcon,
  MapPinned: MockLucideIcon,
}));
