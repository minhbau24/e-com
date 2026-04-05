import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { fetchProductById } from "../api/products";
import { fetchReviews, fetchReviewStats, submitReview } from "../api/reviews";
import LoadingState from "../components/LoadingState";
import { formatPrice } from "../utils/currency";

function StarRow({ value }) {
    return (
        <span className="d-inline-flex align-items-center gap-1 text-warning">
            {[1, 2, 3, 4, 5].map((star) => (
                <span key={star}>{star <= Math.round(value) ? "★" : "☆"}</span>
            ))}
        </span>
    );
}

const DETAIL_FIELD_ALIASES = {
    Publisher: ["Nhà xuất bản", "Nha xuat ban", "Publisher"],
    Pages: ["Số trang", "So trang", "Pages"],
    ISBN: ["ISBN"],
    Size: ["Kích thước", "Kich thuoc", "Size"],
};

const DETAIL_LABEL_LOOKUP = new Map(
    Object.entries(DETAIL_FIELD_ALIASES).flatMap(([field, labels]) =>
        labels.map((label) => [label.toLowerCase(), field]),
    ),
);

function cleanDetailValue(value) {
    return (value || "").replace(/\s+/g, " ").trim().replace(/^[-–—.\s]+|[-–—.\s]+$/g, "");
}

function parseDetails(text) {
    const safe = text || "";
    if (!safe) {
        return {};
    }

    const labelPattern = Object.values(DETAIL_FIELD_ALIASES)
        .flat()
        .map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
        .join("|");
    const matches = [...safe.matchAll(new RegExp(`(?:${labelPattern})\\s*:\\s*`, "gi"))];
    if (!matches.length) {
        return {};
    }

    const details = {};
    for (let index = 0; index < matches.length; index += 1) {
        const match = matches[index];
        const nextMatch = matches[index + 1];
        const label = safe.slice(match.index, match.index + match[0].length).split(":")[0].trim().toLowerCase();
        const field = DETAIL_LABEL_LOOKUP.get(label);
        if (!field || details[field]) {
            continue;
        }

        const value = cleanDetailValue(safe.slice(match.index + match[0].length, nextMatch ? nextMatch.index : safe.length));
        if (value) {
            details[field] = value;
        }
    }

    return details;
}

function extractDetail(label, details) {
    return details?.[label] || "N/A";
}

function ProductDetailPage({ onAddToCart }) {
    const { id } = useParams();
    const navigate = useNavigate();
    const [product, setProduct] = useState(null);
    const [activeImage, setActiveImage] = useState(0);
    const [quantity, setQuantity] = useState(1);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [reviewStats, setReviewStats] = useState(null);
    const [reviews, setReviews] = useState([]);
    const [reviewPage, setReviewPage] = useState(1);
    const [reviewSort, setReviewSort] = useState("newest");
    const [reviewPagination, setReviewPagination] = useState({ has_next: false, total: 0 });
    const [reviewsLoading, setReviewsLoading] = useState(true);

    const [reviewForm, setReviewForm] = useState({ user_name: "", rating: 5, comment: "" });
    const [reviewSubmitting, setReviewSubmitting] = useState(false);
    const [reviewError, setReviewError] = useState("");

    const details = useMemo(() => parseDetails(product?.description), [product?.description]);

    useEffect(() => {
        const load = async () => {
            try {
                setLoading(true);
                const item = await fetchProductById(id);
                setProduct(item || null);
                if (!item) {
                    setError("Product not found");
                }
            } catch (err) {
                setError(err.message || "Failed to load product");
            } finally {
                setLoading(false);
            }
        };

        load();
    }, [id]);

    useEffect(() => {
        const loadReviews = async () => {
            try {
                setReviewsLoading(true);
                const [stats, list] = await Promise.all([
                    fetchReviewStats(id),
                    fetchReviews(id, { sort: reviewSort, page: reviewPage, pageSize: 5 }),
                ]);
                setReviewStats(stats);
                setReviews(list.results || []);
                setReviewPagination(list.pagination || { has_next: false, total: 0 });
            } catch (err) {
                setReviewError(err.message || "Failed to load reviews");
            } finally {
                setReviewsLoading(false);
            }
        };

        loadReviews();
    }, [id, reviewSort, reviewPage]);


    const images = useMemo(() => {
        if (!product) {
            return [];
        }
        const source = [
            product.image_large_url,
            product.image_medium_url,
            product.image_thumbnail_url,
            product.image_small_url,
            product.image_base_url,
        ].filter(Boolean);
        return [...new Set(source)];
    }, [product]);

    if (loading) {
        return <LoadingState text="Loading product detail" />;
    }

    if (error) {
        return <div className="alert alert-danger">{error}</div>;
    }

    const image = images[activeImage] || "https://via.placeholder.com/640x640?text=Product";
    const avgRating = reviewStats?.average_rating || Number(product.rating_average || 4.5);
    const totalReviews = reviewStats?.total_reviews || Number(product.review_count || 0);

    const onSubmitReview = async (e) => {
        e.preventDefault();
        setReviewError("");
        try {
            setReviewSubmitting(true);
            await submitReview(id, {
                user_name: reviewForm.user_name,
                rating: Number(reviewForm.rating),
                comment: reviewForm.comment,
            });
            setReviewForm({ user_name: "", rating: 5, comment: "" });
            setReviewPage(1);
            const [stats, list] = await Promise.all([
                fetchReviewStats(id),
                fetchReviews(id, { sort: reviewSort, page: 1, pageSize: 5 }),
            ]);
            setReviewStats(stats);
            setReviews(list.results || []);
            setReviewPagination(list.pagination || { has_next: false, total: 0 });
        } catch (err) {
            setReviewError(err.response?.data?.detail || err.message || "Cannot submit review");
        } finally {
            setReviewSubmitting(false);
        }
    };

    return (
        <div className="product-detail-wrap">
            <div className="row g-4 align-items-start">
                <div className="col-lg-6">
                    <div className="pd-gallery card border-0 shadow-sm">
                        <div className="pd-main-image-wrap">
                            <img className="pd-main-image" src={image} alt={product.title} />
                        </div>
                        <div className="pd-thumbs d-flex gap-2 p-3 overflow-auto">
                            {images.map((img, idx) => (
                                <button
                                    key={`${img}-${idx}`}
                                    className={`pd-thumb-btn ${idx === activeImage ? "active" : ""}`}
                                    onClick={() => setActiveImage(idx)}
                                    type="button"
                                >
                                    <img src={img} alt={`thumb-${idx}`} className="pd-thumb" />
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="col-lg-6">
                    <div className="d-flex gap-2 flex-wrap mb-2">
                        <span className="badge text-bg-success">In stock</span>
                        <span className="badge text-bg-warning">Best seller</span>
                    </div>

                    <h1 className="pd-title">{product.title}</h1>

                    <div className="d-flex align-items-center gap-2 mb-2">
                        <StarRow value={avgRating} />
                        <span className="small text-muted">{avgRating}/5</span>
                        <span className="small text-muted">({totalReviews} reviews)</span>
                    </div>

                    <div className="pd-price mb-3">{formatPrice(product.price)}</div>

                    <p className="pd-short-desc">{product.short_description || "Premium title with curated design insights."}</p>

                    <div className="pd-sticky-buy card border-0 shadow-sm p-3">
                        <div className="d-flex justify-content-between mb-2">
                            <span className="text-muted">Stock</span>
                            <strong>{product.stock ?? "N/A"}</strong>
                        </div>

                        <div className="d-flex align-items-center gap-2 mb-3">
                            <button type="button" className="btn btn-outline-secondary" onClick={() => setQuantity((v) => Math.max(1, v - 1))}>-</button>
                            <input
                                className="form-control text-center"
                                style={{ maxWidth: 84 }}
                                value={quantity}
                                onChange={(e) => setQuantity(Math.max(1, Number(e.target.value || 1)))}
                            />
                            <button type="button" className="btn btn-outline-secondary" onClick={() => setQuantity((v) => v + 1)}>+</button>
                        </div>

                        <div className="d-grid gap-2">
                            <button className="btn btn-danger btn-lg pd-cta" onClick={() => onAddToCart(product, quantity)}>Add to cart</button>
                            <button
                                className="btn btn-dark btn-lg pd-buy-now"
                                onClick={() => {
                                    onAddToCart(product, quantity);
                                    navigate("/cart");
                                }}
                            >
                                Buy now
                            </button>
                        </div>

                        <div className="d-flex gap-3 mt-3 small text-muted">
                            <button type="button" className="btn btn-link p-0 text-decoration-none">Share</button>
                            <button type="button" className="btn btn-link p-0 text-decoration-none">Wishlist</button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="row g-4 mt-1">
                <div className="col-lg-7">
                    <div className="card border-0 shadow-sm p-4">
                        <h4>Description</h4>
                        <p className="mb-0 text-secondary">{product.description || product.short_description || "No description available."}</p>
                    </div>
                </div>
                <div className="col-lg-5">
                    <div className="card border-0 shadow-sm p-4">
                        <h4>Details</h4>
                        <table className="table table-sm align-middle mb-0">
                            <tbody>
                                <tr><th>Publisher</th><td>{extractDetail("Publisher", details)}</td></tr>
                                <tr><th>Pages</th><td>{extractDetail("Pages", details)}</td></tr>
                                <tr><th>ISBN</th><td>{extractDetail("ISBN", details)}</td></tr>
                                <tr><th>Size</th><td>{extractDetail("Size", details)}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>


            <section className="mt-4">
                <div className="card border-0 shadow-sm p-4">
                    <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
                        <h4 className="m-0">Customer Reviews</h4>
                        <select className="form-select" style={{ maxWidth: 220 }} value={reviewSort} onChange={(e) => { setReviewSort(e.target.value); setReviewPage(1); }}>
                            <option value="newest">Newest</option>
                            <option value="highest">Highest rating</option>
                            <option value="lowest">Lowest rating</option>
                        </select>
                    </div>

                    <div className="row g-4 mb-4">
                        <div className="col-md-4">
                            <div className="pd-review-score">
                                <div className="display-6 fw-bold">{avgRating}</div>
                                <StarRow value={avgRating} />
                                <div className="small text-muted mt-1">{totalReviews} reviews</div>
                            </div>
                        </div>
                        <div className="col-md-8">
                            {[5, 4, 3, 2, 1].map((star) => {
                                const stat = reviewStats?.breakdown?.[String(star)] || { percentage: 0 };
                                return (
                                    <div key={star} className="d-flex align-items-center gap-2 mb-2">
                                        <span className="small" style={{ width: 28 }}>{star}★</span>
                                        <div className="progress flex-grow-1" style={{ height: 8 }}>
                                            <div className="progress-bar bg-warning" style={{ width: `${stat.percentage}%` }} />
                                        </div>
                                        <span className="small text-muted" style={{ width: 56 }}>{stat.percentage}%</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {reviewsLoading ? (
                        <div className="pd-skeleton-wrap">
                            {[1, 2, 3].map((item) => <div key={item} className="pd-skeleton mb-2" />)}
                        </div>
                    ) : (
                        <div>
                            {reviews.map((review) => (
                                <article key={review.id} className="pd-review-item fade-in-up d-flex gap-3">
                                    <div className="pd-avatar">{(review.user_name || "A").charAt(0).toUpperCase()}</div>
                                    <div className="flex-grow-1">
                                        <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
                                            <strong>{review.user_name || "Anonymous"}</strong>
                                            <small className="text-muted">{new Date(review.created_at).toLocaleDateString()}</small>
                                        </div>
                                        <StarRow value={review.rating} />
                                        <p className="mb-0 mt-2 text-secondary">{review.comment || "No comment."}</p>
                                    </div>
                                </article>
                            ))}

                            <div className="d-flex justify-content-between mt-3">
                                <button className="btn btn-outline-secondary" disabled={reviewPage <= 1} onClick={() => setReviewPage((p) => p - 1)}>Previous</button>
                                <button className="btn btn-outline-secondary" disabled={!reviewPagination.has_next} onClick={() => setReviewPage((p) => p + 1)}>Next</button>
                            </div>
                        </div>
                    )}

                    <hr className="my-4" />
                    <h5 className="mb-3">Write a review</h5>
                    <form className="row g-3" onSubmit={onSubmitReview}>
                        <div className="col-md-4">
                            <input
                                className="form-control"
                                placeholder="Name"
                                value={reviewForm.user_name}
                                onChange={(e) => setReviewForm((s) => ({ ...s, user_name: e.target.value }))}
                                required
                            />
                        </div>
                        <div className="col-md-3">
                            <select
                                className="form-select"
                                value={reviewForm.rating}
                                onChange={(e) => setReviewForm((s) => ({ ...s, rating: Number(e.target.value) }))}
                            >
                                {[5, 4, 3, 2, 1].map((star) => <option key={star} value={star}>{star} star</option>)}
                            </select>
                        </div>
                        <div className="col-md-12">
                            <textarea
                                className="form-control"
                                rows="3"
                                placeholder="Comment"
                                value={reviewForm.comment}
                                onChange={(e) => setReviewForm((s) => ({ ...s, comment: e.target.value }))}
                                required
                            />
                        </div>
                        <div className="col-md-12">
                            <button className="btn btn-danger" disabled={reviewSubmitting}>{reviewSubmitting ? "Submitting..." : "Submit review"}</button>
                        </div>
                        {reviewError ? <div className="col-12"><div className="alert alert-danger mb-0">{reviewError}</div></div> : null}
                    </form>
                </div>
            </section>
        </div>
    );
}

export default ProductDetailPage;
