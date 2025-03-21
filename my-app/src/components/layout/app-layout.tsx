import React, { ReactNode } from "react";
import { Model } from "@/types";
import { ModelSelector } from "@/components/ui/model-selector";

interface AppLayoutProps {
  children: ReactNode;
  models: Model[];
  selectedModel: Model;
  onSelectModel: (model: Model) => void;
  isAgentRunning?: boolean;
}

export function AppLayout({
  children,
  models,
  selectedModel,
  onSelectModel,
  isAgentRunning = false,
}: AppLayoutProps) {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center">
          <div className="mr-4 flex">
            <a href="/" className="flex items-center space-x-2">
              <span className="font-bold text-xl">Manus Clone</span>
            </a>
          </div>
          <div className="flex-1"></div>
          <div className="flex items-center">
            <ModelSelector
              models={models}
              selectedModel={selectedModel}
              onSelectModel={onSelectModel}
              disabled={isAgentRunning}
            />
          </div>
        </div>
      </header>
      <main className="flex-1 container py-6">{children}</main>
      <footer className="border-t py-4 px-6">
        <div className="container flex flex-col sm:flex-row items-center justify-between gap-4 md:h-24">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} Manus Clone. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              GitHub
            </a>
            <a
              href="https://manus.im"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Original Manus
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
