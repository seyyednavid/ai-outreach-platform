import { useRef, useState } from "react";
import { Sparkles } from "lucide-react";

import { previewSolutionMatch, type SolutionMatchResponse } from "../api/matching";
import { Badge, Button, Card, CardHeader, Label, Notice, type Tone } from "./ui";
import { getErrorMessage } from "./ui-classes";

interface Props {
  step: number;
  leadId: number | null;
  /** Your company, chosen in the step before. */
  companyId: number | null;
  onMatchChange?: (match: SolutionMatchResponse | null) => void;
}

const confidenceTone: Record<SolutionMatchResponse["confidence"], Tone> = {
  high: "ok",
  medium: "warn",
  low: "bad",
};

/** Remount with a new key when the lead or company changes. */
export default function SolutionMatchingPanel({ step, leadId, companyId, onMatchChange }: Props) {
  const [result, setResult] = useState<SolutionMatchResponse | null>(null);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  async function handleMatch() {
    if (companyId === null || leadId === null || matching) return;
    const requestId = ++requestIdRef.current;
    setMatching(true);
    setError(null);
    setResult(null);
    onMatchChange?.(null);

    try {
      const data = await previewSolutionMatch(companyId, leadId);
      if (requestId !== requestIdRef.current) return;
      setResult(data);
      onMatchChange?.(data.recommended_product_id === null ? null : data);
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setError(getErrorMessage(err, "Product matching failed. Try again."));
    } finally {
      if (requestId === requestIdRef.current) setMatching(false);
    }
  }

  return (
    <Card className="p-5 md:p-6">
      <CardHeader
        step={step}
        title="Match a product"
        tag={<Badge>Optional</Badge>}
        description="The AI picks the product from your catalogue that could fit this lead. Skip it and the email uses your offering text only."
      />

      <div className="mt-5">
        <Button
          variant={result ? "secondary" : "primary"}
          icon={Sparkles}
          loading={matching}
          disabled={companyId === null || leadId === null || matching}
          onClick={() => void handleMatch()}
        >
          {matching ? "Matching…" : result ? "Match again" : "Find best product"}
        </Button>
        {companyId === null && (
          <p className="mt-2 text-xs text-muted">Choose your company first.</p>
        )}
      </div>

      {error && (
        <div className="mt-4">
          <Notice tone="bad">{error}</Notice>
        </div>
      )}

      {result && (
        <div className="mt-5 rounded-md border border-line">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
            <div>
              <Label>Recommended</Label>
              <p className="mt-1 font-display text-lg font-bold">
                {result.recommended_product_name ?? "No product fits"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={confidenceTone[result.confidence]}>
                {result.confidence} confidence
              </Badge>
              <Badge tone={result.customer_need_verified ? "ok" : "warn"}>
                {result.customer_need_verified ? "Need confirmed" : "Need not confirmed"}
              </Badge>
            </div>
          </div>

          <div className="grid gap-5 px-4 py-4 text-sm leading-6 md:grid-cols-2">
            <div>
              <Label>How it could help</Label>
              <p className="mt-1 whitespace-pre-wrap text-ink">{result.potential_use_case}</p>
            </div>
            <div>
              <Label>Why</Label>
              <p className="mt-1 whitespace-pre-wrap text-ink-soft">{result.reasoning}</p>
            </div>
            {result.missing_information.length > 0 && (
              <div className="md:col-span-2">
                <Label>Still unknown</Label>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-ink-soft">
                  {result.missing_information.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
