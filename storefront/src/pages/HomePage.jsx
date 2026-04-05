import { useEffect, useMemo, useState } from "react";
import { fetchAllProducts } from "../api/products";
import LoadingState from "../components/LoadingState";
import ProductCard from "../components/ProductCard";

function HomePage({ onAddToCart }) {
    const [products, setProducts] = useState([]);
    const [keyword, setKeyword] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        const load = async () => {
            try {
                setLoading(true);
                const data = await fetchAllProducts();
                setProducts(data);
            } catch (err) {
                setError(err.message || "Failed to load products");
            } finally {
                setLoading(false);
            }
        };

        load();
    }, []);

    const filtered = useMemo(() => {
        const q = keyword.toLowerCase().trim();
        if (!q) {
            return products;
        }
        return products.filter((item) => (item.title || "").toLowerCase().includes(q));
    }, [products, keyword]);

    if (loading) {
        return <LoadingState text="Loading products" />;
    }

    if (error) {
        return <div className="alert alert-danger">{error}</div>;
    }

    return (
        <div>
            <section className="hero-surface rounded-4 p-4 p-md-5 mb-4 text-white">
                <h2 className="mb-2">Daily Drops. Clean Commerce.</h2>
                <p className="mb-0">A storefront clone wired to your Django microservices via API Gateway.</p>
            </section>

            <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
                <h4 className="m-0">Products ({filtered.length})</h4>
                <input
                    type="text"
                    className="form-control w-auto"
                    placeholder="Search products"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                />
            </div>

            <div className="row g-3">
                {filtered.map((item) => (
                    <ProductCard key={`${item.productType || "product"}-${item.id}`} product={item} onAdd={onAddToCart} />
                ))}
            </div>
        </div>
    );
}

export default HomePage;
