
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";

export interface Company {
  id: number;
  name: string;
  website: string | null;
  industry: string;
  description: string;
  target_customers: string;
  differentiators: string;
}

export type CompanyInput = Omit<Company, "id">;

export interface Product {
  id: number;
  company_id: number;
  name: string;
  description: string;
  features: string[];
  use_cases: string[];
}

export type ProductInput = Omit<Product, "id" | "company_id">;

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    try {
      const error = await response.json();

      if (typeof error.detail === "string") {
        message = error.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function getCompanies(): Promise<Company[]> {
  const response = await fetch(`${API_BASE_URL}/companies`);
  return parseResponse<Company[]>(response);
}

export async function createCompany(
  data: CompanyInput,
): Promise<Company> {
  const response = await fetch(`${API_BASE_URL}/companies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  return parseResponse<Company>(response);
}

export async function updateCompany(
  companyId: number,
  data: CompanyInput,
): Promise<Company> {
  const response = await fetch(
    `${API_BASE_URL}/companies/${companyId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
  );

  return parseResponse<Company>(response);
}

export async function getProducts(
  companyId: number,
): Promise<Product[]> {
  const response = await fetch(
    `${API_BASE_URL}/companies/${companyId}/products`,
  );

  return parseResponse<Product[]>(response);
}

export async function createProduct(
  companyId: number,
  data: ProductInput,
): Promise<Product> {
  const response = await fetch(
    `${API_BASE_URL}/companies/${companyId}/products`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
  );

  return parseResponse<Product>(response);
}

export async function updateProduct(
  companyId: number,
  productId: number,
  data: ProductInput,
): Promise<Product> {
  const response = await fetch(
    `${API_BASE_URL}/companies/${companyId}/products/${productId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
  );

  return parseResponse<Product>(response);
}

export async function deleteProduct(
  companyId: number,
  productId: number,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/companies/${companyId}/products/${productId}`,
    { method: "DELETE" },
  );

  if (!response.ok) {
    await parseResponse<unknown>(response);
  }

  // HTTP 204 has no response body.
}