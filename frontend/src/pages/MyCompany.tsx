
import { useEffect, useState, type FormEvent } from "react";
import {
  Building2,
  LoaderCircle,
  Package,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  X,
} from "lucide-react";

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

const emptyCompany: CompanyInput = {
  name: "",
  website: null,
  industry: "",
  description: "",
  target_customers: "",
  differentiators: "",
};

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

const inputClass =
  "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 " +
  "text-sm outline-none focus:border-indigo-500 focus:ring-2 " +
  "focus:ring-indigo-100";

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
      [field]: field === "website" ? value || null : value,
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
    <div className="space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold">My Company</h2>
          <p className="mt-2 text-slate-500">
            Manage your company profiles and products.
          </p>
        </div>

        <button
          type="button"
          onClick={startNewCompany}
          disabled={busy}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Plus size={18} />
          Add Company
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {success && (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
        >
          {success}
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Building2 size={20} className="text-indigo-600" />
          <h3 className="font-semibold">Select Company</h3>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">
            Loading companies...
          </p>
        ) : (
          <select
            className={inputClass}
            value={companyId ?? ""}
            disabled={busy}
            onChange={(event) =>
              selectCompany(
                event.target.value
                  ? Number(event.target.value)
                  : null,
              )
            }
          >
            <option value="">Choose a company...</option>

            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        )}
      </section>

      {companyFormVisible && (
        <form
          onSubmit={(event) => void handleSaveCompany(event)}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <h3 className="mb-5 text-lg font-semibold">
            {creatingCompany ? "New Company" : "Edit Company"}
          </h3>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm font-medium">
              Company Name *
              <input
                className={inputClass}
                required
                disabled={busy}
                value={companyForm.name}
                onChange={(e) =>
                  updateCompanyField("name", e.target.value)
                }
              />
            </label>

            <label className="space-y-2 text-sm font-medium">
              Website
              <input
                type="url"
                className={inputClass}
                disabled={busy}
                placeholder="https://example.com"
                value={companyForm.website ?? ""}
                onChange={(e) =>
                  updateCompanyField("website", e.target.value)
                }
              />
            </label>

            <label className="space-y-2 text-sm font-medium">
              Industry *
              <input
                className={inputClass}
                required
                disabled={busy}
                value={companyForm.industry}
                onChange={(e) =>
                  updateCompanyField("industry", e.target.value)
                }
              />
            </label>

            <label className="space-y-2 text-sm font-medium">
              Target Customers *
              <input
                className={inputClass}
                required
                disabled={busy}
                value={companyForm.target_customers}
                onChange={(e) =>
                  updateCompanyField("target_customers", e.target.value)
                }
              />
            </label>

            <label className="space-y-2 text-sm font-medium md:col-span-2">
              Company Description *
              <textarea
                className={inputClass}
                rows={4}
                required
                disabled={busy}
                value={companyForm.description}
                onChange={(e) =>
                  updateCompanyField("description", e.target.value)
                }
              />
            </label>

            <label className="space-y-2 text-sm font-medium md:col-span-2">
              Key Differentiators *
              <textarea
                className={inputClass}
                rows={3}
                required
                disabled={busy}
                value={companyForm.differentiators}
                onChange={(e) =>
                  updateCompanyField("differentiators", e.target.value)
                }
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={busy}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? (
                <LoaderCircle size={17} className="animate-spin" />
              ) : (
                <Save size={17} />
              )}
              Save Company
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setCreatingCompany(false);
                setEditingCompany(false);
              }}
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm"
            >
              <X size={17} />
              Cancel
            </button>
          </div>
        </form>
      )}

      {selectedCompany && !companyFormVisible && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold">
                {selectedCompany.name}
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                {selectedCompany.industry}
              </p>
            </div>

            <button
              type="button"
              onClick={startEditCompany}
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              <Pencil size={16} />
              Edit Company
            </button>
          </div>

          {selectedCompany.website && (
            <a
              href={selectedCompany.website}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block text-sm text-indigo-600 hover:underline"
            >
              {selectedCompany.website}
            </a>
          )}

          <div className="mt-5 space-y-4 text-sm">
            <div>
              <p className="font-semibold">Description</p>
              <p className="mt-1 whitespace-pre-wrap text-slate-600">
                {selectedCompany.description}
              </p>
            </div>

            <div>
              <p className="font-semibold">Target Customers</p>
              <p className="mt-1 whitespace-pre-wrap text-slate-600">
                {selectedCompany.target_customers}
              </p>
            </div>

            <div>
              <p className="font-semibold">Differentiators</p>
              <p className="mt-1 whitespace-pre-wrap text-slate-600">
                {selectedCompany.differentiators}
              </p>
            </div>
          </div>
        </section>
      )}

      {selectedCompany && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Package size={20} className="text-indigo-600" />
              <h3 className="text-lg font-semibold">
                Products ({products.length})
              </h3>
            </div>

            <button
              type="button"
              onClick={startNewProduct}
              disabled={busy}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              <Plus size={17} />
              Add Product
            </button>
          </div>

          {showProductForm && (
            <form
              onSubmit={(event) => void handleSaveProduct(event)}
              className="mb-6 space-y-4 rounded-xl border border-indigo-200 bg-indigo-50/40 p-5"
            >
              <h4 className="font-semibold">
                {editingProductId === null
                  ? "New Product"
                  : "Edit Product"}
              </h4>

              <label className="block space-y-2 text-sm font-medium">
                Product Name *
                <input
                  className={inputClass}
                  required
                  disabled={busy}
                  value={productForm.name}
                  onChange={(e) =>
                    updateProductField("name", e.target.value)
                  }
                />
              </label>

              <label className="block space-y-2 text-sm font-medium">
                Description *
                <textarea
                  className={inputClass}
                  rows={3}
                  required
                  disabled={busy}
                  value={productForm.description}
                  onChange={(e) =>
                    updateProductField("description", e.target.value)
                  }
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2 text-sm font-medium">
                  Features (one per line)
                  <textarea
                    className={inputClass}
                    rows={5}
                    disabled={busy}
                    value={productForm.featuresText}
                    onChange={(e) =>
                      updateProductField(
                        "featuresText",
                        e.target.value,
                      )
                    }
                    placeholder={
                      "Service point calling\nVisual customer guidance"
                    }
                  />
                </label>

                <label className="block space-y-2 text-sm font-medium">
                  Use Cases (one per line)
                  <textarea
                    className={inputClass}
                    rows={5}
                    disabled={busy}
                    value={productForm.useCasesText}
                    onChange={(e) =>
                      updateProductField(
                        "useCasesText",
                        e.target.value,
                      )
                    }
                    placeholder={
                      "Retail service counters\nCustomer service desks"
                    }
                  />
                </label>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={busy}
                  className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {saving ? (
                    <LoaderCircle size={17} className="animate-spin" />
                  ) : (
                    <Save size={17} />
                  )}
                  Save Product
                </button>

                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setShowProductForm(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {loadingProducts ? (
            <p className="text-sm text-slate-500">
              Loading products...
            </p>
          ) : products.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-500">
              No products yet. Add your first product.
            </p>
          ) : (
            <div className="space-y-4">
              {products.map((product) => (
                <div
                  key={product.id}
                  className="rounded-xl border border-slate-200 p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h4 className="font-semibold">
                        {product.name}
                      </h4>
                      <p className="mt-2 text-sm text-slate-600">
                        {product.description}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => startEditProduct(product)}
                        className="rounded-lg border border-slate-200 p-2 hover:bg-slate-50 disabled:opacity-50"
                        aria-label={`Edit ${product.name}`}
                      >
                        <Pencil size={17} />
                      </button>

                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          void handleDeleteProduct(product)
                        }
                        className="rounded-lg border border-red-200 p-2 text-red-600 hover:bg-red-50 disabled:opacity-50"
                        aria-label={`Delete ${product.name}`}
                      >
                        {deletingId === product.id ? (
                          <LoaderCircle
                            size={17}
                            className="animate-spin"
                          />
                        ) : (
                          <Trash2 size={17} />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Features
                      </p>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                        {product.features.map((feature, index) => (
                          <li key={index}>{feature}</li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Use Cases
                      </p>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                        {product.use_cases.map((useCase, index) => (
                          <li key={index}>{useCase}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {!selectedCompany && !creatingCompany && !loading && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <Building2
            size={32}
            className="mx-auto text-slate-400"
          />
          <p className="mt-3 text-sm text-slate-500">
            Select a company or create a new company profile.
          </p>
        </div>
      )}

      <p className="flex items-center gap-2 text-xs text-slate-400">
        <RefreshCw size={13} />
        Company information and products are stored in PostgreSQL.
      </p>
    </div>
  );
}