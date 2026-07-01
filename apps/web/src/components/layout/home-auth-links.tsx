"use client";

import Link from "next/link";

import { SignOutButton } from "@/components/layout/sign-out-button";

export function HomeAuthLinks({
  signInClassName,
  registerClassName,
  signOutClassName,
}: {
  signInClassName: string;
  registerClassName?: string;
  signOutClassName: string;
}) {
  return (
    <>
      <Link className={signInClassName} href="/login/">
        Sign in
      </Link>
      <Link className={registerClassName ?? signInClassName} href="/register">
        Register
      </Link>
      <SignOutButton plain className={signOutClassName} />
    </>
  );
}
