"use client";

import { useEffect, useState } from "react";

import { fetchHomeBackgroundImageUrls } from "@/lib/home-backgrounds";

export function useHomeBackgroundImageUrls(initialImageUrls: string[] = []) {
  const [imageUrls, setImageUrls] = useState(initialImageUrls);

  useEffect(() => {
    let cancelled = false;

    if (imageUrls.length > 0) {
      return;
    }

    void fetchHomeBackgroundImageUrls().then((nextImageUrls) => {
      if (!cancelled && nextImageUrls.length > 0) {
        setImageUrls(nextImageUrls);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [imageUrls.length]);

  return imageUrls;
}
