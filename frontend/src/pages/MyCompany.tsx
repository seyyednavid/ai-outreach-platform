import { useEffect, useState, type FormEvent } from "react";
import { Building2, Package, Pencil, Plus, Save, Trash2, X } from "lucide-react";

import {
  createCompany,
  createProduct,
  deleteProduct,
  getCompanies,
  getProducts,
  updateCompany,
  updateProduct,
  type Company,
  type CompanyInput,
  type Product,
  type ProductInput,
} from "../api/companies";
import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Label,
  Notice,
  PageHeader,
} from "../components/ui";
import { inputClass } from "../components/ui-classes";

const emptyCompany: CompanyInput = {
  name: "",
  website: null,
  industry: "",
  description: "",
  target_customers: "",
  differentiators: "",
  sender_name: null,
  sender_job_title: null,
  sign_off: "Best regards",
  sender_email: null,
  sender_phone: null,
  cta_type: "call",
};

/** Optional text fields saved as null when left empty. */
const OPTIONAL_FIELDS: (keyof CompanyInput)[] = [
  "website",
  "sender_name",
  "sender_job_title",
  "sign_off",
  "sender_email",
  "sender_phone",
];

/** The same block the backend adds to every email. */
function signaturePreview(company: CompanyInput): string | null {
  if (!company.sender_name) return null;
  const titleLine = [company.sender_job_title, company.name].filter(Boolean).join(", ");
  const contactLine = [company.sender_phone, company.sender_email].filter(Boolean).join(" · ");
  return [
    `${(company.sign_off || "Best regards").replace(/,$/, "")},`,
    company.sender_name,
    titleLine,
    contactLine,
  ]
    .filter(Boolean)
    .join("\n");
}

interface ProductForm {
  name: string;
  description: string;
  featuresText: string;
  useCasesText: string;
}

const emptyProduct: ProductForm = {
  name: "",
  description: "",
  featuresText: "",
  useCasesText: "",
};

function listToText(items: string[]): string {
  return items.join("\n");
}

function textToList(text: string): string[] {
  return text
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong";
}

export default function MyCompany() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [products, setProducts] = useState<Product[]>([]);

  const [companyForm, setCompanyForm] = useState<CompanyInput>({
    ...emptyCompany,
  });

  const [productForm, setProductForm] = useState<ProductForm>({
    ...emptyProduct,
  });

  const [creatingCompany, setCreatingCompany] = useState(false);
  const [editingCompany, setEditingCompany] = useState(false);
  const [showProductForm, setShowProductForm] = useState(false);
  const [editingProductId, setEditingProductId] = useState<number | null>(
    null,
  );

  const [loading, setLoading] = useState(true);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const selectedCompany =
    companies.find((company) => company.id === companyId) ?? null;

  useEffect(() => {
    let cancelled = false;

    getCompanies()
      .then((data) => {
        if (!cancelled) {
          setCompanies(data);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(getErrorMessage(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (companyId === null) return;

    let cancelled = false;

    getProducts(companyId)
      .then((data) => {
        if (!cancelled) {
          setProducts(data);
          setLoadingProducts(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(getErrorMessage(err));
          setLoadingProducts(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [companyId]);

  function selectCompany(id: number | null) {
    setCompanyId(id);
    setProducts([]);
    setLoadingProducts(id !== null);
    setCreatingCompany(false);
    setEditingCompany(false);
    setShowProductForm(false);
    setEditingProductId(null);
    setError(null);
    setSuccess(null);
  }

  function startNewCompany() {
    selectCompany(null);
    setCompanyForm({ ...emptyCompany });
    setCreatingCompany(true);
  }

  function startEditCompany() {
    if (!selectedCompany) return;

    setCompanyForm({
      name: selectedCompany.name,
      website: selectedCompany.website,
      industry: selectedCompany.industry,
      description: selectedCompany.description,
      target_customers: selectedCompany.target_customers,
      differentiators: selectedCompany.differentiators,
      sender_name: selectedCompany.sender_name,
      sender_job_title: selectedCompany.sender_job_title,
      sign_off: selectedCompany.sign_off,
      sender_email: selectedCompany.sender_email,
      sender_phone: selectedCompany.sender_phone,
      cta_type: selectedCompany.cta_type,
    });

    setEditingCompany(true);
    setError(null);
    setSuccess(null);
  }

  function updateCompanyField(
    field: keyof CompanyInput,
    value: string,
  ) {
    setCompanyForm((current) => ({
      ...current,
      [field]: OPTIONAL_FIELDS.includes(field) ? value || null : value,
    }));
  }

  async function handleSaveCompany(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      if (creatingCompany) {
        const created = await createCompany(companyForm);

        setCompanies((current) => [created, ...current]);
        selectCompany(created.id);
        setSuccess("Company created successfully.");
      } else if (companyId !== null) {
        const updated = await updateCompany(
          companyId,
          companyForm,
        );

        setCompanies((current) =>
          current.map((company) =>
            company.id === updated.id ? updated : company,
          ),
        );

        setEditingCompany(false);
        setSuccess("Company updated successfully.");
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  function startNewProduct() {
    setProductForm({ ...emptyProduct });
    setEditingProductId(null);
    setShowProductForm(true);
    setError(null);
    setSuccess(null);
  }

  function startEditProduct(product: Product) {
    setProductForm({
      name: product.name,
      description: product.description,
      featuresText: listToText(product.features),
      useCasesText: listToText(product.use_cases),
    });

    setEditingProductId(product.id);
    setShowProductForm(true);
    setError(null);
    setSuccess(null);
  }

  function updateProductField(
    field: keyof ProductForm,
    value: string,
  ) {
    setProductForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSaveProduct(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (companyId === null) return;

    const companyIdAtSubmit = companyId;

    const data: ProductInput = {
      name: productForm.name.trim(),
      description: productForm.description.trim(),
      features: textToList(productForm.featuresText),
      use_cases: textToList(productForm.useCasesText),
    };

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      if (editingProductId !== null) {
        const updated = await updateProduct(
          companyIdAtSubmit,
          editingProductId,
          data,
        );

        setProducts((current) =>
          current.map((product) =>
            product.id === updated.id ? updated : product,
          ),
        );

        setSuccess("Product updated successfully.");
      } else {
        const created = await createProduct(
          companyIdAtSubmit,
          data,
        );

        setProducts((current) => [created, ...current]);
        setSuccess("Product added successfully.");
      }

      setShowProductForm(false);
      setEditingProductId(null);
      setProductForm({ ...emptyProduct });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteProduct(product: Product) {
    if (companyId === null) return;

    const confirmed = window.confirm(
      `Delete "${product.name}"? This action cannot be undone.`,
    );

    if (!confirmed) return;

    setDeletingId(product.id);
    setError(null);
    setSuccess(null);

    try {
      await deleteProduct(companyId, product.id);

      setProducts((current) =>
        current.filter((item) => item.id !== product.id),
      );

      setSuccess("Product deleted successfully.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  }

  const companyFormVisible = creatingCompany || editingCompany;
  const busy = saving || deletingId !== null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="My Company"
        description="What you sell. The AI may only describe products using what you write here."
        actions={
          <Button icon={Plus} disabled={busy} onClick={startNewCompany}>
            Add company
          </Button>
        }
      />

      {error && <Notice tone="bad">{error}</Notice>}
      {success && (
        <Notice tone="ok" role="status">
          {success}
        </Notice>
      )}

      <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        {/* Company list */}
        <nav aria-label="Companies" className="min-w-0">
          <Label>Companies</Label>
          {loading ? (
            <p className="mt-3 text-sm text-muted">Loading…</p>
          ) : companies.length === 0 ? (
            <p className="mt-3 text-sm leading-6 text-muted">None yet.</p>
          ) : (
            <ul className="mt-3 flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible">
              {companies.map((company) => {
                const active = company.id === companyId && !creatingCompany;
                return (
                  <li key={company.id} className="shrink-0">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => selectCompany(company.id)}
                      aria-current={active ? "true" : undefined}
                      className={`w-full rounded-md border px-3.5 py-2.5 text-left text-sm transition-colors disabled:opacity-50 ${
                        active
                          ? "border-ink bg-ink text-white"
                          : "border-line bg-surface hover:border-line-strong"
                      }`}
                    >
                      <span className="block font-semibold">{company.name}</span>
                      <span className={`block text-xs ${active ? "text-white/60" : "text-muted"}`}>
                        {company.industry}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </nav>

        <div className="min-w-0 space-y-4">
          {/* Company form */}
          {companyFormVisible && (
            <Card as="div" className="p-5 md:p-6">
              <form onSubmit={(event) => void handleSaveCompany(event)}>
                <CardHeader
                  icon={Building2}
                  title={creatingCompany ? "New company" : `Edit ${selectedCompany?.name ?? "company"}`}
                  description="Fields marked * are required."
                />

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <Field label="Company name *">
                    <input
                      className={inputClass}
                      required
                      disabled={busy}
                      value={companyForm.name}
                      onChange={(e) => updateCompanyField("name", e.target.value)}
                    />
                  </Field>
                  <Field label="Website">
                    <input
                      type="url"
                      className={inputClass}
                      disabled={busy}
                      placeholder="https://example.com"
                      value={companyForm.website ?? ""}
                      onChange={(e) => updateCompanyField("website", e.target.value)}
                    />
                  </Field>
                  <Field label="Industry *">
                    <input
                      className={inputClass}
                      required
                      disabled={busy}
                      value={companyForm.industry}
                      onChange={(e) => updateCompanyField("industry", e.target.value)}
                    />
                  </Field>
                  <Field label="Who you sell to *">
                    <input
                      className={inputClass}
                      required
                      disabled={busy}
                      value={companyForm.target_customers}
                      onChange={(e) => updateCompanyField("target_customers", e.target.value)}
                    />
                  </Field>
                  <Field label="Description *" className="md:col-span-2">
                    <textarea
                      className={`${inputClass} leading-6`}
                      rows={4}
                      required
                      disabled={busy}
                      value={companyForm.description}
                      onChange={(e) => updateCompanyField("description", e.target.value)}
                    />
                  </Field>
                  <Field label="What sets you apart *" className="md:col-span-2">
                    <textarea
                      className={`${inputClass} leading-6`}
                      rows={3}
                      required
                      disabled={busy}
                      value={companyForm.differentiators}
                      onChange={(e) => updateCompanyField("differentiators", e.target.value)}
                    />
                  </Field>

                  <div className="border-t border-line pt-5 md:col-span-2">
                    <p className="font-semibold text-ink">Email signature and ending</p>
                    <p className="mt-1 text-sm text-muted">
                      Added to the end of every email by the app, never written by the AI.
                      Without your name, drafts cannot pass review.
                    </p>
                  </div>
                  <Field label="Your name" hint="Recommended">
                    <input
                      className={inputClass}
                      disabled={busy}
                      placeholder="Jane Smith"
                      value={companyForm.sender_name ?? ""}
                      onChange={(e) => updateCompanyField("sender_name", e.target.value)}
                    />
                  </Field>
                  <Field label="Your job title">
                    <input
                      className={inputClass}
                      disabled={busy}
                      placeholder="Sales Manager"
                      value={companyForm.sender_job_title ?? ""}
                      onChange={(e) => updateCompanyField("sender_job_title", e.target.value)}
                    />
                  </Field>
                  <Field label="Phone">
                    <input
                      type="tel"
                      className={inputClass}
                      disabled={busy}
                      placeholder="+44 20 0000 0000"
                      value={companyForm.sender_phone ?? ""}
                      onChange={(e) => updateCompanyField("sender_phone", e.target.value)}
                    />
                  </Field>
                  <Field label="Email">
                    <input
                      type="email"
                      className={inputClass}
                      disabled={busy}
                      placeholder="jane@company.com"
                      value={companyForm.sender_email ?? ""}
                      onChange={(e) => updateCompanyField("sender_email", e.target.value)}
                    />
                  </Field>
                  <Field label="Sign-off">
                    <input
                      className={inputClass}
                      disabled={busy}
                      placeholder="Best regards"
                      value={companyForm.sign_off ?? ""}
                      onChange={(e) => updateCompanyField("sign_off", e.target.value)}
                    />
                  </Field>
                  <fieldset className="text-sm">
                    <legend className="font-medium text-ink">Every email ends by asking for</legend>
                    <div className="mt-1.5 flex flex-col gap-2">
                      {(
                        [
                          ["call", "A short phone call"],
                          ["email", "A reply by email"],
                        ] as const
                      ).map(([value, label]) => (
                        <label key={value} className="flex cursor-pointer items-center gap-2 text-ink">
                          <input
                            type="radio"
                            name="cta_type"
                            className="size-4 accent-petrol"
                            disabled={busy}
                            checked={companyForm.cta_type === value}
                            onChange={() => updateCompanyField("cta_type", value)}
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  <Button type="submit" icon={Save} loading={saving} disabled={busy}>
                    Save company
                  </Button>
                  <Button
                    variant="ghost"
                    icon={X}
                    disabled={busy}
                    onClick={() => {
                      setCreatingCompany(false);
                      setEditingCompany(false);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {/* Company profile */}
          {selectedCompany && !companyFormVisible && (
            <Card className="p-5 md:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-2xl font-bold tracking-tight">{selectedCompany.name}</h2>
                  <p className="mt-1 text-sm text-muted">
                    {selectedCompany.industry}
                    {selectedCompany.website && (
                      <>
                        {" · "}
                        <a
                          href={selectedCompany.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-petrol hover:underline"
                        >
                          {selectedCompany.website.replace(/^https?:\/\//, "")}
                        </a>
                      </>
                    )}
                  </p>
                </div>
                <Button variant="secondary" size="sm" icon={Pencil} onClick={startEditCompany}>
                  Edit
                </Button>
              </div>

              <dl className="mt-5 grid gap-5 text-sm leading-6 md:grid-cols-3">
                {(
                  [
                    ["Description", selectedCompany.description],
                    ["Who you sell to", selectedCompany.target_customers],
                    ["What sets you apart", selectedCompany.differentiators],
                  ] as const
                ).map(([label, value]) => (
                  <div key={label}>
                    <dt><Label>{label}</Label></dt>
                    <dd className="mt-1 whitespace-pre-wrap text-ink-soft">{value}</dd>
                  </div>
                ))}
              </dl>

              <div className="mt-6 border-t border-line pt-5">
                <Label>Email signature and ending</Label>
                {signaturePreview(selectedCompany) ? (
                  <div className="mt-2 grid gap-4 text-sm md:grid-cols-2">
                    <pre className="whitespace-pre-wrap rounded-md border border-line bg-paper/60 px-4 py-3 font-sans leading-6 text-ink">
                      {signaturePreview(selectedCompany)}
                    </pre>
                    <p className="leading-6 text-ink-soft">
                      Every email ends by asking for{" "}
                      <strong className="text-ink">
                        {selectedCompany.cta_type === "email" ? "a reply by email" : "a short phone call"}
                      </strong>
                      . The app adds this signature itself, so it is always correct.
                    </p>
                  </div>
                ) : (
                  <div className="mt-2">
                    <Notice tone="warn" title="Add your name to sign emails">
                      Without a sender name, every draft fails review. Click Edit to add it.
                    </Notice>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Product catalogue */}
          {selectedCompany && (
            <Card className="p-5 md:p-6">
              <CardHeader
                icon={Package}
                title={`Products (${products.length})`}
                description="Matching picks from this list, and the email may only claim these features."
                actions={
                  !showProductForm && (
                    <Button size="sm" icon={Plus} disabled={busy} onClick={startNewProduct}>
                      Add product
                    </Button>
                  )
                }
              />

              {showProductForm && (
                <form
                  onSubmit={(event) => void handleSaveProduct(event)}
                  className="mt-5 space-y-4 rounded-md border border-petrol/30 bg-petrol-wash/40 p-4 md:p-5"
                >
                  <p className="font-semibold">
                    {editingProductId === null ? "New product" : "Edit product"}
                  </p>
                  <Field label="Product name *">
                    <input
                      className={inputClass}
                      required
                      disabled={busy}
                      value={productForm.name}
                      onChange={(e) => updateProductField("name", e.target.value)}
                    />
                  </Field>
                  <Field label="Description *">
                    <textarea
                      className={`${inputClass} leading-6`}
                      rows={3}
                      required
                      disabled={busy}
                      value={productForm.description}
                      onChange={(e) => updateProductField("description", e.target.value)}
                    />
                  </Field>
                  <div className="grid gap-4 md:grid-cols-2">
                    <Field label="Features" hint="One per line">
                      <textarea
                        className={`${inputClass} leading-6`}
                        rows={5}
                        disabled={busy}
                        value={productForm.featuresText}
                        onChange={(e) => updateProductField("featuresText", e.target.value)}
                        placeholder={"Service point calling\nVisual customer guidance"}
                      />
                    </Field>
                    <Field label="Use cases" hint="One per line">
                      <textarea
                        className={`${inputClass} leading-6`}
                        rows={5}
                        disabled={busy}
                        value={productForm.useCasesText}
                        onChange={(e) => updateProductField("useCasesText", e.target.value)}
                        placeholder={"Retail service counters\nCustomer service desks"}
                      />
                    </Field>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button type="submit" icon={Save} loading={saving} disabled={busy}>
                      Save product
                    </Button>
                    <Button variant="ghost" disabled={busy} onClick={() => setShowProductForm(false)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              )}

              <div className="mt-5">
                {loadingProducts ? (
                  <p className="text-sm text-muted">Loading products…</p>
                ) : products.length === 0 ? (
                  <EmptyState icon={Package} title="No products yet">
                    Add at least one product so the AI can match it to your leads.
                  </EmptyState>
                ) : (
                  <ul className="divide-y divide-line border-y border-line">
                    {products.map((product) => (
                      <li key={product.id} className="py-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="font-semibold text-ink">{product.name}</p>
                            <p className="mt-1 text-sm leading-6 text-ink-soft">{product.description}</p>
                          </div>
                          <div className="flex gap-1.5">
                            <Button
                              variant="secondary"
                              size="sm"
                              icon={Pencil}
                              disabled={busy}
                              onClick={() => startEditProduct(product)}
                              aria-label={`Edit ${product.name}`}
                            />
                            <Button
                              variant="danger"
                              size="sm"
                              icon={Trash2}
                              loading={deletingId === product.id}
                              disabled={busy}
                              onClick={() => void handleDeleteProduct(product)}
                              aria-label={`Delete ${product.name}`}
                            />
                          </div>
                        </div>

                        {(product.features.length > 0 || product.use_cases.length > 0) && (
                          <div className="mt-3 grid gap-4 text-sm md:grid-cols-2">
                            {(
                              [
                                ["Features", product.features],
                                ["Use cases", product.use_cases],
                              ] as const
                            ).map(([label, items]) =>
                              items.length === 0 ? null : (
                                <div key={label}>
                                  <Label>{label}</Label>
                                  <ul className="mt-1.5 flex flex-wrap gap-1.5">
                                    {items.map((item, index) => (
                                      <li
                                        key={index}
                                        className="rounded border border-line bg-paper/60 px-2 py-0.5 text-[13px] text-ink-soft"
                                      >
                                        {item}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ),
                            )}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Card>
          )}

          {!selectedCompany && !creatingCompany && !loading && (
            <EmptyState
              icon={Building2}
              title={companies.length === 0 ? "Add your company" : "Choose a company"}
              action={
                companies.length === 0 && (
                  <Button icon={Plus} onClick={startNewCompany}>
                    Add company
                  </Button>
                )
              }
            >
              {companies.length === 0
                ? "Describe what you sell. The AI uses this to match products and write accurate emails."
                : "Pick a company on the left to see its profile and products."}
            </EmptyState>
          )}
        </div>
      </div>
    </div>
  );
}

