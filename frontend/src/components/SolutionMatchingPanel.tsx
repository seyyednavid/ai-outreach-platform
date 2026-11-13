
import { useEffect, useState } from "react";
import {
  AlertCircle,
  BrainCircuit,
  CheckCircle2,
  LoaderCircle,
  PackageSearch,
  Sparkles,
} from "lucide-react";

import {
  getCompanies,
  type Company,
} from "../api/companies";

import {
  previewSolutionMatch,
  type SolutionMatchResponse,
} from "../api/matching";

interface Props {
  leadId: number | null;
}

export default function SolutionMatchingPanel({
  leadId,
}: Props) {
  console.trace("SolutionMatchingPanel rendered");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [result, setResult] =
    useState<SolutionMatchResponse | null>(null);

  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getCompanies()
      .then((data) => {
        if (cancelled) return;

        setCompanies(data);

        if (data.length === 1) {
          setCompanyId(data[0].id);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load companies",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingCompanies(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleMatch() {
    if (companyId === null || leadId === null) return;

    const selectedCompanyId = companyId;
    const selectedLeadId = leadId;

    setMatching(true);
    setError(null);
    setResult(null);

    try {
      const data = await previewSolutionMatch(
        selectedCompanyId,
        selectedLeadId,
      );

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Solution matching failed",
      );
    } finally {
      setMatching(false);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-start gap-3">
        <div className="rounded-xl bg-indigo-100 p-3 text-indigo-600">
          <BrainCircuit size={22} />
        </div>

        <div>
          <h2 className="text-lg font-semibold">
            AI Solution Matching 
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Find the most relevant product for your selected lead.
          </p>
        </div>
      </div>

      <label className="block space-y-2 text-sm font-medium">
        Seller Company

        <select
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-indigo-500"
          value={companyId ?? ""}
          disabled={loadingCompanies || matching}
          onChange={(event) => {
            setCompanyId(
              event.target.value
                ? Number(event.target.value)
                : null,
            );
            setResult(null);
            setError(null);
          }}
        >
          <option value="">Select your company...</option>

          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
      </label>

      <button
        type="button"
        onClick={() => void handleMatch()}
        disabled={
          companyId === null ||
          leadId === null ||
          matching ||
          loadingCompanies
        }
        className="mt-4 flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {matching ? (
          <LoaderCircle size={18} className="animate-spin" />
        ) : (
          <Sparkles size={18} />
        )}

        {matching ? "Matching products..." : "Find Best Solution"}
      </button>

      {leadId === null && (
        <p className="mt-3 flex items-center gap-2 text-sm text-amber-700">
          <AlertCircle size={16} />
          Please select a lead first.
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700"
        >
          {error}
        </p>
      )}

      {result && (
        <div className="mt-6 space-y-5 rounded-xl border border-indigo-100 bg-indigo-50/40 p-5">
          <div className="flex items-center gap-2">
            <PackageSearch size={20} className="text-indigo-600" />
            <h3 className="font-semibold">
              Matching Result
            </h3>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Recommended Product
            </p>
            <p className="mt-1 text-lg font-bold">
              {result.recommended_product_name ??
                "No suitable product identified"}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
              Confidence: {result.confidence}
            </span>

            <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
              {result.customer_need_verified
                ? "Customer need verified"
                : "Customer need not verified"}
            </span>
          </div>

          <div>
            <h4 className="text-sm font-semibold">
              Potential Use Case
            </h4>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">
              {result.potential_use_case}
            </p>
          </div>

          <div>
            <h4 className="text-sm font-semibold">
              AI Reasoning
            </h4>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">
              {result.reasoning}
            </p>
          </div>

          <div>
            <h4 className="text-sm font-semibold">
              Missing Information
            </h4>

            {result.missing_information.length > 0 ? (
              <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-slate-600">
                {result.missing_information.map(
                  (item, index) => (
                    <li key={index}>{item}</li>
                  ),
                )}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-500">
                No additional information listed.
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 border-t border-indigo-100 pt-4 text-xs text-slate-500">
            {result.customer_need_verified ? (
              <CheckCircle2
                size={16}
                className="text-emerald-600"
              />
            ) : (
              <AlertCircle
                size={16}
                className="text-amber-600"
              />
            )}

            Review the recommendation before using it in outreach.
          </div>
        </div>
      )}
    </section>
  );
}
