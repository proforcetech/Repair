"use client";

import { ChangeEvent } from "react";

import {
  EstimateItemDraft,
  LaborItemDraft,
  PartItemDraft,
  calculateDraftCost,
} from "@/services/estimates";

type LaborItemEditorProps = {
  items: LaborItemDraft[];
  onChange: (items: LaborItemDraft[]) => void;
};

export function LaborItemEditor({ items, onChange }: LaborItemEditorProps) {
  const handleChange = (
    index: number,
    field: keyof Omit<LaborItemDraft, "kind">,
    value: string,
  ) => {
    const next = [...items];
    const parsed = field === "description" ? value : Number.parseFloat(value) || 0;
    next[index] = {
      ...next[index],
      [field]: field === "description" ? value : parsed,
    } as LaborItemDraft;
    onChange(next);
  };

  const handleAdd = () => {
    onChange([
      ...items,
      { kind: "labor", description: "", hours: 1, rate: 100 },
    ]);
  };

  const handleRemove = (index: number) => {
    const next = items.filter((_, i) => i !== index);
    onChange(next);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Labor</h3>
        <button
          type="button"
          className="rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground transition hover:bg-primary/90"
          onClick={handleAdd}
        >
          Add labor line
        </button>
      </div>
      <div className="space-y-2">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No labor added yet. Use the button above to create your first line.
          </p>
        ) : (
          items.map((item, index) => (
            <LaborRow
              key={`labor-${index}`}
              item={item}
              onChange={(field, value) => handleChange(index, field, value)}
              onRemove={() => handleRemove(index)}
            />
          ))
        )}
      </div>
    </div>
  );
}

type LaborRowProps = {
  item: LaborItemDraft;
  onChange: (field: keyof Omit<LaborItemDraft, "kind">, value: string) => void;
  onRemove: () => void;
};

function LaborRow({ item, onChange, onRemove }: LaborRowProps) {
  const handleNumberChange = (field: "hours" | "rate") =>
    (event: ChangeEvent<HTMLInputElement>) => {
      onChange(field, event.target.value);
    };

  return (
    <div className="rounded-md border border-border/70 p-3 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <label className="flex-1 text-sm">
          <span className="mb-1 block font-medium text-foreground">Description</span>
          <input
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            value={item.description}
            onChange={(event) => onChange("description", event.target.value)}
            placeholder="Describe the labor"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-foreground">Hours</span>
          <input
            type="number"
            min={0}
            step={0.25}
            className="w-24 rounded-md border border-border/70 bg-background px-2 py-2 text-sm text-right shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            value={item.hours}
            onChange={handleNumberChange("hours")}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-foreground">Rate</span>
          <input
            type="number"
            min={0}
            step={1}
            className="w-24 rounded-md border border-border/70 bg-background px-2 py-2 text-sm text-right shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            value={item.rate}
            onChange={handleNumberChange("rate")}
          />
        </label>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-foreground">
            ${calculateDraftCost(item).toFixed(2)}
          </span>
          <button
            type="button"
            onClick={onRemove}
            className="text-xs font-medium text-destructive hover:underline"
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  );
}

type PartItemEditorProps = {
  items: PartItemDraft[];
  onChange: (items: PartItemDraft[]) => void;
};

export function PartItemEditor({ items, onChange }: PartItemEditorProps) {
  const handleChange = (
    index: number,
    field: keyof Omit<PartItemDraft, "kind">,
    value: string,
  ) => {
    const next = [...items];
    const parsed =
      field === "description" || field === "partNumber"
        ? value
        : Number.parseFloat(value) || 0;
    next[index] = {
      ...next[index],
      [field]: field === "description" || field === "partNumber" ? value : parsed,
    } as PartItemDraft;
    onChange(next);
  };

  const handleAdd = () => {
    onChange([
      ...items,
      { kind: "part", description: "", unitPrice: 0, quantity: 1, partNumber: "" },
    ]);
  };

  const handleRemove = (index: number) => {
    const next = items.filter((_, i) => i !== index);
    onChange(next);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Parts</h3>
        <button
          type="button"
          className="rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground transition hover:bg-primary/90"
          onClick={handleAdd}
        >
          Add part line
        </button>
      </div>
      <div className="space-y-2">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No parts selected. Use the button above to add components.
          </p>
        ) : (
          items.map((item, index) => (
            <PartRow
              key={`part-${index}`}
              item={item}
              onChange={(field, value) => handleChange(index, field, value)}
              onRemove={() => handleRemove(index)}
            />
          ))
        )}
      </div>
    </div>
  );
}

type PartRowProps = {
  item: PartItemDraft;
  onChange: (field: keyof Omit<PartItemDraft, "kind">, value: string) => void;
  onRemove: () => void;
};

function PartRow({ item, onChange, onRemove }: PartRowProps) {
  const handleNumberChange = (field: "unitPrice" | "quantity") =>
    (event: ChangeEvent<HTMLInputElement>) => {
      onChange(field, event.target.value);
    };

  return (
    <div className="rounded-md border border-border/70 p-3 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <label className="flex-1 text-sm">
          <span className="mb-1 block font-medium text-foreground">Description</span>
          <input
            className="w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            value={item.description}
            onChange={(event) => onChange("description", event.target.value)}
            placeholder="Describe the part"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-foreground">Part #</span>
          <input
            className="w-32 rounded-md border border-border/70 bg-background px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            value={item.partNumber ?? ""}
            onChange={(event) => onChange("partNumber", event.target.value)}
            placeholder="SKU"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-foreground">Qty</span>
          <input
            type="number"
            min={0}
            step={1}
            className="w-20 rounded-md border border-border/70 bg-background px-2 py-2 text-sm text-right shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            value={item.quantity}
            onChange={handleNumberChange("quantity")}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-foreground">Unit price</span>
          <input
            type="number"
            min={0}
            step={0.01}
            className="w-24 rounded-md border border-border/70 bg-background px-2 py-2 text-sm text-right shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            value={item.unitPrice}
            onChange={handleNumberChange("unitPrice")}
          />
        </label>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-foreground">
            ${calculateDraftCost(item).toFixed(2)}
          </span>
          <button
            type="button"
            onClick={onRemove}
            className="text-xs font-medium text-destructive hover:underline"
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  );
}

export function summarizeDrafts(items: EstimateItemDraft[]) {
  const total = items.reduce((acc, item) => acc + calculateDraftCost(item), 0);
  return total;
}
