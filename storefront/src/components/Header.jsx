import { Link, NavLink } from "react-router-dom";

function Header({ cartCount, currentUser, onLogout }) {
    return (
        <header className="navbar navbar-expand-lg bg-white border-bottom sticky-top">
            <div className="container">
                <Link className="navbar-brand fw-bold text-danger" to="/">
                    ShopClone
                </Link>

                <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav">
                    <span className="navbar-toggler-icon"></span>
                </button>

                <div className="collapse navbar-collapse" id="mainNav">
                    <ul className="navbar-nav me-auto mb-2 mb-lg-0">
                        <li className="nav-item">
                            <NavLink className="nav-link" to="/">
                                Home
                            </NavLink>
                        </li>
                        {!currentUser ? (
                            <li className="nav-item">
                                <NavLink className="nav-link" to="/auth">
                                    Account
                                </NavLink>
                            </li>
                        ) : null}
                    </ul>

                    <div className="d-flex align-items-center gap-2">
                        {currentUser ? (
                            <>
                                <span className="small text-muted">Hi, {currentUser.name}</span>
                                <button className="btn btn-sm btn-outline-secondary" onClick={onLogout}>
                                    Logout
                                </button>
                            </>
                        ) : null}
                        <Link to="/cart" className="btn btn-outline-dark position-relative">
                            Cart
                            <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
                                {cartCount}
                            </span>
                        </Link>
                    </div>
                </div>
            </div>
        </header>
    );
}

export default Header;
