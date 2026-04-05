import apiClient from "./client";

export async function fetchBooks() {
    const response = await apiClient.get("/books/");
    return response.data;
}

export async function fetchClothes() {
    const response = await apiClient.get("/clothes/");
    return response.data;
}

export async function fetchAllProducts() {
    const [books, clothes] = await Promise.allSettled([fetchBooks(), fetchClothes()]);

    const bookItems = books.status === "fulfilled" ? books.value : [];
    const clothesItems = clothes.status === "fulfilled" ? clothes.value : [];

    const withType = [
        ...bookItems.map((item) => ({ ...item, productType: "book" })),
        ...clothesItems.map((item) => ({ ...item, productType: "clothes" })),
    ];

    return withType;
}

export async function fetchProductById(id) {
    const all = await fetchAllProducts();
    return all.find((item) => String(item.id) === String(id));
}

