import { useMemo, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { addToCart, removeCartItem, updateCartQuantity } from "./api/cart";
import AuthPage from "./pages/AuthPage";
import ChatWidget from "./components/ChatWidget";
import Header from "./components/Header";
import CartPage from "./pages/CartPage";
import HomePage from "./pages/HomePage";
import ProductDetailPage from "./pages/ProductDetailPage";
import { loadCart, saveCart } from "./utils/storage";

function App() {
  const [cartItems, setCartItems] = useState(loadCart());
  const [currentUser, setCurrentUser] = useState(() => {
    const raw = localStorage.getItem("current_user");
    return raw ? JSON.parse(raw) : null;
  });

  const cartCount = useMemo(
    () => cartItems.reduce((sum, item) => sum + Number(item.quantity || 0), 0),
    [cartItems],
  );

  const onAddToCart = async (product, quantity = 1) => {
    const existing = cartItems.find((item) => String(item.id) === String(product.id));
    const nextItems = existing
      ? cartItems.map((item) =>
        String(item.id) === String(product.id)
          ? { ...item, quantity: item.quantity + quantity }
          : item,
      )
      : [...cartItems, { ...product, quantity }];

    setCartItems(nextItems);
    saveCart(nextItems);

    try {
      await addToCart({
        product_id: product.id,
        quantity,
        customer_id: currentUser?.id,
        product_type: product.productType || product.source_category || "book",
      });
    } catch (error) {
      console.error("Cart API error", error?.response?.data || error.message);
    }
  };

  const updateQty = async (id, quantity) => {
    const safeQuantity = Math.max(1, quantity);
    const previous = cartItems;
    const targetItem = cartItems.find((item) => String(item.id) === String(id));
    const next = previous
      .map((item) => (String(item.id) === String(id) ? { ...item, quantity: safeQuantity } : item))
      .filter((item) => item.quantity > 0);

    setCartItems(next);
    saveCart(next);

    if (!currentUser?.id || !targetItem) {
      return;
    }

    try {
      await updateCartQuantity({
        customer_id: currentUser.id,
        product_id: targetItem.id,
        quantity: safeQuantity,
      });
    } catch (error) {
      console.error("Update cart quantity failed", error?.response?.data || error.message);
      setCartItems(previous);
      saveCart(previous);
    }
  };

  const removeItem = async (id) => {
    const previous = cartItems;
    const targetItem = cartItems.find((item) => String(item.id) === String(id));
    const next = previous.filter((item) => String(item.id) !== String(id));

    setCartItems(next);
    saveCart(next);

    if (!currentUser?.id || !targetItem) {
      return;
    }

    try {
      await removeCartItem({
        customer_id: currentUser.id,
        product_id: targetItem.id,
      });
    } catch (error) {
      console.error("Remove cart item failed", error?.response?.data || error.message);
      setCartItems(previous);
      saveCart(previous);
    }
  };

  const onCheckoutSuccess = () => {
    setCartItems([]);
    saveCart([]);
  };

  const onAuthSuccess = (data) => {
    if (data?.token) {
      localStorage.setItem("jwt_token", data.token);
    }
    if (data?.customer) {
      localStorage.setItem("current_user", JSON.stringify(data.customer));
      setCurrentUser(data.customer);
    }
  };

  const onLogout = () => {
    localStorage.removeItem("jwt_token");
    localStorage.removeItem("current_user");
    setCurrentUser(null);
  };

  return (
    <div className="min-vh-100 app-shell">
      <Header cartCount={cartCount} currentUser={currentUser} onLogout={onLogout} />
      <main className="container py-4">
        <Routes>
          <Route path="/" element={<HomePage onAddToCart={onAddToCart} />} />
          <Route path="/products/:id" element={<ProductDetailPage onAddToCart={onAddToCart} />} />
          <Route
            path="/cart"
            element={<CartPage cartItems={cartItems} updateQty={updateQty} removeItem={removeItem} currentUser={currentUser} onCheckoutSuccess={onCheckoutSuccess} />}
          />
          <Route path="/auth" element={<AuthPage onAuthSuccess={onAuthSuccess} />} />
        </Routes>
      </main>
      <ChatWidget currentUser={currentUser} />
    </div>
  );
}

export default App;
