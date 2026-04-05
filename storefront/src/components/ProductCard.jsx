import { Link } from "react-router-dom";
import { formatPrice } from "../utils/currency";

function ProductCard({ product, onAdd }) {
    const image =
        product.image_medium_url || product.image_small_url || product.image_thumbnail_url || product.image_base_url ||
        "https://via.placeholder.com/320x320?text=Product";

    return (
        <div className="col-12 col-sm-6 col-md-4 col-xl-3 d-flex">
            <div className="card h-100 shadow-sm product-card w-100">
                <img src={image} className="card-img-top" alt={product.title} />
                <div className="card-body d-flex flex-column">
                    <small className="text-muted text-uppercase">{product.productType || product.source_category || "item"}</small>
                    <h6 className="card-title mt-1 line-clamp-2">{product.title}</h6>
                    <div className="fw-semibold text-danger mb-3">{formatPrice(product.price)}</div>

                    <div className="d-flex gap-2 mt-auto">
                        <Link to={`/products/${product.id}`} className="btn btn-outline-secondary btn-sm w-50">
                            Detail
                        </Link>
                        <button className="btn btn-danger btn-sm w-50" onClick={() => onAdd(product)}>
                            Add
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ProductCard;
