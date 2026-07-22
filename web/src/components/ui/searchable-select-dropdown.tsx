"use client";

import clsx from "clsx";
import { useEffect, useRef, useState } from "react";

type SearchableSelectOption = {
  label: string;
  value: string;
};

type SearchableSelectGroup = {
  label: string;
  options: readonly SearchableSelectOption[];
};

type SearchableSelectDropdownProps = {
  placeholder: string;
  value: string;
  displayValue?: string;
  groups: readonly SearchableSelectGroup[];
  disabled?: boolean;
  hasError?: boolean;
  className?: string;
  panelClassName?: string;
  summaryClassName?: string;
  emptyStateText?: string;
  searchPlaceholder?: string;
  onChange: (value: string) => void;
};

export function SearchableSelectDropdown({
  placeholder,
  value,
  displayValue,
  groups,
  disabled = false,
  hasError,
  className,
  panelClassName,
  summaryClassName,
  emptyStateText = "No options available.",
  searchPlaceholder = "Type to search universities",
  onChange,
}: SearchableSelectDropdownProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleClickOutside(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      setQuery("");
      return;
    }

    searchInputRef.current?.focus();
  }, [isOpen]);

  const normalizedQuery = query.trim().toLowerCase();
  const visibleGroups = normalizedQuery
    ? groups
        .map((group) => ({
          ...group,
          options: group.options.filter((option) => option.label.toLowerCase().includes(normalizedQuery)),
        }))
        .filter((group) => group.options.length > 0)
    : groups;

  return (
    <div ref={containerRef} className={clsx("relative", className)}>
      <button
        type="button"
        onClick={() => !disabled && setIsOpen((current) => !current)}
        disabled={disabled}
        className={clsx(
          "flex min-h-[50px] w-full items-center justify-between rounded-2xl border bg-transparent px-4 py-3 text-left text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md transition focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:border-white/8 disabled:text-slate-400",
          hasError
            ? "border-2 border-red-500 ring-2 ring-red-500/45 focus:border-red-500 focus:ring-red-500/50"
            : "border-white/10 focus:border-white/20 focus:ring-lime/25",
          value ? "text-white" : "text-[grey]"
        )}
      >
        <span className={clsx("pr-3", summaryClassName)}>{displayValue || value || placeholder}</span>
        <span
          className={clsx(
            "text-xs font-semibold uppercase tracking-[0.18em] text-slate-300 transition",
            isOpen ? "rotate-180" : ""
          )}
        >
          v
        </span>
      </button>

      {isOpen ? (
        <div
          className={clsx(
            "absolute left-0 right-0 top-[calc(100%+0.5rem)] z-30 max-h-80 overflow-y-auto rounded-3xl border border-white/12 bg-[#0A1E15]/95 p-3 shadow-[0_24px_60px_rgba(0,0,0,0.38)] backdrop-blur-xl",
            panelClassName
          )}
        >
          <div className="mb-3">
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={searchPlaceholder}
              className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-sm placeholder:text-[grey] focus:border-white/20 focus:ring-2 focus:ring-lime/25"
            />
          </div>

          {visibleGroups.length === 0 ? (
            <p className="px-3 py-2 text-sm text-mist">{emptyStateText}</p>
          ) : (
            <div className="grid gap-3">
              {visibleGroups.map((group) => (
                <div key={group.label} className="grid gap-2">
                  <p className="px-3 text-[11px] uppercase tracking-[0.22em] text-lime">
                    {group.label}
                  </p>
                  <div className="grid gap-2">
                    {group.options.map((option) => {
                      const isSelected = value === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => {
                            onChange(option.value);
                            setIsOpen(false);
                          }}
                          className={clsx(
                            "flex w-full items-start justify-between gap-3 rounded-2xl border px-3 py-2 text-left text-sm transition",
                            isSelected
                              ? "border-lime/50 bg-lime/10 text-[grey]"
                              : "border-white/8 bg-white/[0.04] text-[grey] hover:border-lime/50 hover:bg-white/[0.08] hover:text-white"
                          )}
                        >
                          <span>{option.label}</span>
                          {isSelected ? (
                            <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-lime">
                              Selected
                            </span>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
