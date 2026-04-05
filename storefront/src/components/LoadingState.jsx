function LoadingState({ text = "Loading..." }) {
    return (
        <div className="d-flex justify-content-center align-items-center py-5 gap-2">
            <div className="spinner-border text-danger" role="status"></div>
            <span>{text}</span>
        </div>
    );
}

export default LoadingState;
