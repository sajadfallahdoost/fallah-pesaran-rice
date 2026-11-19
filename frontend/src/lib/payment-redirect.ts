"use client";

import { api } from "@/lib/api-client";

interface PaymentRedirect {
  url: string;
  method: "GET" | "POST";
  params: Record<string, string> | null;
}

/** Starts a gateway attempt and sends the browser to the bank page. */
export async function goToGateway(orderNumber: string, token: string, provider: string): Promise<void> {
  const redirect = await api<PaymentRedirect>(`/orders/${encodeURIComponent(orderNumber)}/pay/`, {
    method: "POST",
    body: { provider, token },
  });
  if (redirect.method === "POST") {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = redirect.url;
    for (const [name, value] of Object.entries(redirect.params ?? {})) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = value;
      form.appendChild(input);
    }
    document.body.appendChild(form);
    form.submit();
    return;
  }
  const target = new URL(redirect.url, window.location.origin);
  for (const [name, value] of Object.entries(redirect.params ?? {})) target.searchParams.set(name, value);
  window.location.assign(target.toString());
}
