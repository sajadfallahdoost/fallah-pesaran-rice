"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { api } from "@/lib/api-client";
import type { Cart } from "@/lib/types";

interface CartState {
  cart: Cart | null;
  count: number;
  loading: boolean;
  refresh: () => Promise<Cart | null>;
  setCart: (cart: Cart) => void;
  announce: (message: string) => void;
  announcement: string;
}

const CartContext = createContext<CartState | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCartState] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [announcement, setAnnouncement] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api<Cart>("/cart/");
      setCartState(data);
      return data;
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial sync with the server-side cart
    void refresh();
  }, [refresh]);

  const announce = useCallback((message: string) => {
    setAnnouncement(message);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setAnnouncement(""), 4000);
  }, []);

  const value = useMemo<CartState>(
    () => ({
      cart,
      count: cart?.item_count ?? 0,
      loading,
      refresh,
      setCart: setCartState,
      announce,
      announcement,
    }),
    [cart, loading, refresh, announce, announcement],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartState {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used inside CartProvider");
  return context;
}
