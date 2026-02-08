'use client';

import { useEffect, useState } from 'react';
import { PlatformConfig, api } from '@/lib/api-client';

interface DemoBannerProps {
  platformConfig?: PlatformConfig | null;
  className?: string;
}

export function DemoBanner({ platformConfig, className }: DemoBannerProps) {
  const [fetchedConfig, setFetchedConfig] = useState<PlatformConfig | null>(null);
  const config = platformConfig === undefined ? fetchedConfig : platformConfig;

  useEffect(() => {
    if (platformConfig !== undefined) return;

    let active = true;
    api
      .getPlatformConfig()
      .then((data) => {
        if (active) setFetchedConfig(data);
      })
      .catch(() => {
        if (active) setFetchedConfig(null);
      });

    return () => {
      active = false;
    };
  }, [platformConfig]);

  if (!config?.demo_mode) return null;

  return (
    <div className={className}>
      <div className="border-b border-indigo-500/30 bg-indigo-500/10 text-indigo-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-2.5 text-xs sm:text-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <span>{config.demo_banner_text}</span>
          <a
            href="https://github.com/ShreeBohara/codebaseqa#live-demo-mode"
            target="_blank"
            rel="noreferrer"
            className="text-indigo-300 hover:text-indigo-100 underline underline-offset-2"
          >
            Bring your own repo and API key
          </a>
        </div>
      </div>
    </div>
  );
}
