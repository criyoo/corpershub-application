"use client";

import clsx from "clsx";
import { useEffect, useRef, useState } from "react";

type MultiSelectGroup = {
  label: string;
  options: readonly string[];
};

type MultiSelectDropdownProps = {
  placeholder: string;
  values: string[];
  groups: readonly MultiSelectGroup[];
  exclusiveOption?: string;
  disabled?: boolean;
  className?: string;
  panelClassName?: string;
  summaryClassName?: string;
  emptyStateText?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
  onChange: (values: string[]) => void;
};

function toggleSelection(currentValues: string[], option: string) {
  return currentValues.includes(option)
    ? currentValues.filter((value) => value !== option)
    : [...currentValues, option];
}

function normalizeValues(currentValues: string[], exclusiveOption?: string) {
  const normalizedValues = Array.from(
    new Set(currentValues.map((value) => value.trim()).filter(Boolean))
  );
  if (!exclusiveOption || !normalizedValues.includes(exclusiveOption)) {
    return normalizedValues;
  }
  return [exclusiveOption];
}

export function MultiSelectDropdown({
  placeholder,
  values,
  groups,
  exclusiveOption,
  disabled = false,
  className,
  panelClassName,
  summaryClassName,
  emptyStateText = "No options available.",
  searchable = false,
  searchPlaceholder = "Type to filter options",
  onChange,
}: MultiSelectDropdownProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selectedValues = normalizeValues(values, exclusiveOption);
  const hasExclusiveSelection = Boolean(
    exclusiveOption && selectedValues.includes(exclusiveOption)
  );

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
    if (searchable) {
      searchInputRef.current?.focus();
    }
  }, [isOpen, searchable]);

  const selectedSummary = (() => {
    if (selectedValues.length === 0) {
      return placeholder;
    }
    if (selectedValues.length <= 2) {
      return selectedValues.join(", ");
    }
    return `${selectedValues.slice(0, 2).join(", ")} +${selectedValues.length - 2} more`;
  })();

  const normalizedQuery = query.trim().toLowerCase();
  const visibleGroups = normalizedQuery
    ? groups
        .map((group) => ({
          ...group,
          options: group.options.filter((option) => option.toLowerCase().includes(normalizedQuery)),
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
          "flex min-h-[50px] w-full items-center justify-between rounded-2xl border border-white/10 bg-transparent px-4 py-3 text-left text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md transition focus:border-white/20 focus:outline-none focus:ring-2 focus:ring-lime/25 disabled:cursor-not-allowed disabled:border-white/8 disabled:text-slate-400",
          selectedValues.length === 0 ? "text-white/45" : "text-white"
        )}
      >
        <span className={clsx("pr-3", summaryClassName)}>{selectedSummary}</span>
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
          {searchable ? (
            <div className="mb-3">
              <input
                ref={searchInputRef}
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-sm placeholder:text-white/45 focus:border-white/20 focus:ring-2 focus:ring-lime/25"
              />
            </div>
          ) : null}
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
                      const isSelected = selectedValues.includes(option);
                      const isOptionDisabled =
                        disabled || (hasExclusiveSelection && option !== exclusiveOption);
                      return (
                        <label
                          key={option}
                          className={clsx(
                            "flex items-start gap-3 rounded-2xl border border-white/8 bg-white/[0.04] px-3 py-2 text-sm transition",
                            isOptionDisabled
                              ? "cursor-not-allowed text-white/25"
                              : "cursor-pointer text-[grey] hover:border-lime/50 hover:bg-white/[0.08] hover:text-white"
                          )}
                        >
                          <input
                            type="checkbox"
                            className="mt-1 h-4 w-4 rounded border-white/20 bg-transparent accent-[#1FB766]"
                            checked={isSelected}
                            disabled={isOptionDisabled}
                            onChange={() =>
                              onChange(
                                normalizeValues(
                                  toggleSelection(selectedValues, option),
                                  exclusiveOption
                                )
                              )
                            }
                          />
                          <span>{option}</span>
                        </label>
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
