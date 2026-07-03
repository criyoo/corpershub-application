import "@testing-library/jest-dom";
import { createElement } from "react";
import { vi } from "vitest";

const MockLucideIcon = (props: Record<string, unknown>) => createElement("svg", props);

vi.mock("lucide-react", () => ({
  ArrowLeft: MockLucideIcon,
  Eye: MockLucideIcon,
  EyeOff: MockLucideIcon,
}));
