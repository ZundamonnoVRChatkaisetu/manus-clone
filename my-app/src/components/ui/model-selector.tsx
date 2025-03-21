import React from "react";
import { Model } from "@/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./select";

interface ModelSelectorProps {
  models: Model[];
  selectedModel: Model;
  onSelectModel: (model: Model) => void;
  disabled?: boolean;
}

export function ModelSelector({
  models,
  selectedModel,
  onSelectModel,
  disabled = false,
}: ModelSelectorProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor="model-selector" className="text-sm font-medium">
        モデル
      </label>
      <Select
        disabled={disabled}
        value={selectedModel.id}
        onValueChange={(value) => {
          const model = models.find((m) => m.id === value);
          if (model) {
            onSelectModel(model);
          }
        }}
      >
        <SelectTrigger id="model-selector" className="w-[260px]">
          <SelectValue placeholder="モデルを選択" />
        </SelectTrigger>
        <SelectContent>
          {models.map((model) => (
            <SelectItem key={model.id} value={model.id}>
              <div className="flex flex-col">
                <span className="font-medium">{model.name}</span>
                <span className="text-xs text-muted-foreground">
                  {model.description}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
