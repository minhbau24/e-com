import os
import time
import requests
from django.http import HttpResponse
from django.template.loader import render_to_string
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import GatewayRequestLog

SERVICE_MAP = {
    "customer": os.getenv("CUSTOMER_SERVICE_URL", "http://customer-service:8000"),
    "staff": os.getenv("STAFF_SERVICE_URL", "http://staff-service:8000"),
    "manager": os.getenv("MANAGER_SERVICE_URL", "http://manager-service:8000"),
    "book": os.getenv("BOOK_SERVICE_URL", "http://book-service:8000"),
    "catalog": os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8000"),
    "cart": os.getenv("CART_SERVICE_URL", "http://cart-service:8000"),
    "order": os.getenv("ORDER_SERVICE_URL", "http://order-service:8000"),
    "pay": os.getenv("PAY_SERVICE_URL", "http://pay-service:8000"),
    "ship": os.getenv("SHIP_SERVICE_URL", "http://ship-service:8000"),
    "comment-rate": os.getenv("COMMENT_RATE_SERVICE_URL", "http://comment-rate-service:8000"),
    "ecom": os.getenv("ECOM_API_URL", "http://ecom-api:8000"),
    "search": os.getenv("SEARCH_API_URL", "http://search-api:8001"),
}

DEFAULT_TIMEOUT_SECONDS = int(os.getenv("GATEWAY_TIMEOUT_SECONDS", "30"))


def request_with_retry(method, url, payload=None, retries=3, delay=1, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
    last_error = None
    for _ in range(retries):
        try:
            if method == "GET":
                return requests.get(url, timeout=timeout_seconds)
            if method == "POST":
                return requests.post(url, json=payload, timeout=timeout_seconds)
            if method == "PUT":
                return requests.put(url, json=payload, timeout=timeout_seconds)
            if method == "DELETE":
                return requests.delete(url, timeout=timeout_seconds)
        except requests.RequestException as exc:
            last_error = str(exc)
            if retries > 1:
                time.sleep(delay)
    raise requests.RequestException(last_error)


class ProxyAPIView(APIView):
    def dispatch_request(self, method, service, subpath, payload=None):
        base = SERVICE_MAP.get(service)
        if not base:
            return Response({"detail": "Unknown service"}, status=404)
        target = f"{base}/{subpath}" if subpath else f"{base}/"
        if method == "GET" and self.request.query_params:
            query = self.request.query_params.urlencode()
            target = f"{target}?{query}"
        response = request_with_retry(method, target, payload)
        GatewayRequestLog.objects.create(service=service, path=subpath or "/", status_code=response.status_code)
        data = response.json() if response.content else {"detail": "ok"}
        return Response(data, status=response.status_code)

    def get(self, request, service, subpath=""):
        return self.dispatch_request("GET", service, subpath)

    def post(self, request, service, subpath=""):
        return self.dispatch_request("POST", service, subpath, request.data)

    def put(self, request, service, subpath=""):
        return self.dispatch_request("PUT", service, subpath, request.data)

    def delete(self, request, service, subpath=""):
        return self.dispatch_request("DELETE", service, subpath)


class BooksGatewayAPIView(APIView):
    def get(self, request):
        try:
            response = request_with_retry("GET", f"{SERVICE_MAP['book']}/books/")
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Book service unavailable", "error": str(exc)}, status=503)

    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['book']}/books/", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Book service unavailable", "error": str(exc)}, status=503)


class ClothesGatewayAPIView(APIView):
    def get(self, request):
        return Response([])

    def post(self, request):
        return Response({"detail": "Clothes service not configured in this workspace."}, status=501)


class CustomersGatewayAPIView(APIView):
    def get(self, request):
        try:
            response = request_with_retry("GET", f"{SERVICE_MAP['customer']}/customers/")
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Customer service unavailable", "error": str(exc)}, status=503)

    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['customer']}/customers/", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Customer service unavailable", "error": str(exc)}, status=503)


class OrdersGatewayAPIView(APIView):
    def get(self, request):
        try:
            response = request_with_retry("GET", f"{SERVICE_MAP['order']}/orders/")
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Order service unavailable", "error": str(exc)}, status=503)

    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['order']}/orders/", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Order service unavailable", "error": str(exc)}, status=503)


class CartAddGatewayAPIView(APIView):
    def post(self, request):
        try:
            customer_id = request.data.get("customer_id") or 1
            product_id = request.data.get("product_id")
            quantity = int(request.data.get("quantity", 1))

            if not product_id:
                return Response({"detail": "product_id is required"}, status=400)

            cart_resp = request_with_retry("POST", f"{SERVICE_MAP['cart']}/carts/", {"customer_id": customer_id})
            if cart_resp.status_code < 400:
                cart_id = cart_resp.json().get("id")
            else:
                # Customer can already have an ACTIVE cart due to unique constraint on customer_id.
                carts_resp = request_with_retry("GET", f"{SERVICE_MAP['cart']}/carts/")
                if carts_resp.status_code >= 400:
                    return Response({"detail": "Cannot load cart"}, status=carts_resp.status_code)
                carts = carts_resp.json() if carts_resp.content else []
                existing = next((item for item in carts if str(item.get("customer_id")) == str(customer_id)), None)
                if not existing:
                    return Response({"detail": "Cannot create or load cart"}, status=400)
                cart_id = existing.get("id")

            if not cart_id:
                return Response({"detail": "Cannot resolve cart id"}, status=400)

            item_payload = {
                "cart": cart_id,
                "book_id": product_id,
                "quantity": quantity,
            }
            item_resp = request_with_retry("POST", f"{SERVICE_MAP['cart']}/cart-items/", item_payload)
            return Response(item_resp.json(), status=item_resp.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Cart service unavailable", "error": str(exc)}, status=503)


class RegisterGatewayAPIView(APIView):
    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['customer']}/auth/register/", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Customer service unavailable", "error": str(exc)}, status=503)


class LoginGatewayAPIView(APIView):
    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['customer']}/auth/login/", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Customer service unavailable", "error": str(exc)}, status=503)


class ProductReviewsGatewayAPIView(APIView):
    def get(self, request, product_id):
        try:
            query = request.query_params.urlencode()
            target = f"{SERVICE_MAP['comment-rate']}/products/{product_id}/reviews/"
            if query:
                target = f"{target}?{query}"
            response = request_with_retry("GET", target, timeout_seconds=300)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Review service unavailable", "error": str(exc)}, status=503)

    def post(self, request, product_id):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['comment-rate']}/products/{product_id}/reviews/", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Review service unavailable", "error": str(exc)}, status=503)


class ProductReviewStatsGatewayAPIView(APIView):
    def get(self, request, product_id):
        try:
            response = request_with_retry("GET", f"{SERVICE_MAP['comment-rate']}/products/{product_id}/reviews/stats/")
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Review service unavailable", "error": str(exc)}, status=503)


class BookListHTMLAPIView(APIView):
    def get(self, request):
        try:
            response = request_with_retry("GET", f"{SERVICE_MAP['book']}/books/")
            books = response.json() if response.status_code < 400 else []
        except requests.RequestException:
            books = []
        html = render_to_string("core/book_list.html", {"books": books})
        return HttpResponse(html)


class CartHTMLAPIView(APIView):
    def get(self, request, cart_id):
        try:
            response = request_with_retry("GET", f"{SERVICE_MAP['cart']}/carts/{cart_id}/")
            cart = response.json() if response.status_code < 400 else {}
        except requests.RequestException:
            cart = {}
        html = render_to_string("core/cart_view.html", {"cart": cart})
        return HttpResponse(html)


class SearchGatewayAPIView(APIView):
    def get(self, request):
        try:
            query = request.query_params.urlencode()
            target = f"{SERVICE_MAP['search']}/search"
            if query:
                target = f"{target}?{query}"
            response = request_with_retry("GET", target)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Search service unavailable", "error": str(exc)}, status=503)

    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['search']}/search", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "Search service unavailable", "error": str(exc)}, status=503)


class EcomChatGatewayAPIView(APIView):
    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['ecom']}/chat", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "E-com chat service unavailable", "error": str(exc)}, status=503)


class EcomRecommendGatewayAPIView(APIView):
    def get(self, request, user_id):
        try:
            response = request_with_retry("GET", f"{SERVICE_MAP['ecom']}/recommend/{user_id}")
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "E-com recommend service unavailable", "error": str(exc)}, status=503)


class EcomTrackGatewayAPIView(APIView):
    def post(self, request):
        try:
            response = request_with_retry("POST", f"{SERVICE_MAP['ecom']}/track", request.data)
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as exc:
            return Response({"detail": "E-com tracking service unavailable", "error": str(exc)}, status=503)
