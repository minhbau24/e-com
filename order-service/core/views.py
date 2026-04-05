import logging
import os
import time
import requests
from decimal import Decimal
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, OrderItem
from .serializers import OrderSerializer

logger = logging.getLogger(__name__)
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://cart-service:8000")
PAY_SERVICE_URL = os.getenv("PAY_SERVICE_URL", "http://pay-service:8000")
SHIP_SERVICE_URL = os.getenv("SHIP_SERVICE_URL", "http://ship-service:8000")
BOOK_SERVICE_URL = os.getenv("BOOK_SERVICE_URL", "http://book-service:8000")


def request_with_retry(method, url, payload=None, retries=3, base_delay=1):
    """Retry logic with exponential backoff"""
    last_error = None
    for attempt in range(retries):
        try:
            timeout = 5
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=payload, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, json=payload, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code < 500:
                return response
            # Retry on server errors
            last_error = f"Server error: {response.status_code}"
            
        except requests.RequestException as exc:
            last_error = str(exc)
        
        if attempt < retries - 1:
            delay = base_delay * (2 ** attempt)  # Exponential backoff
            logger.warning("Retry attempt %d/%d after %ds. Error: %s", attempt + 1, retries, delay, last_error)
            time.sleep(delay)
    
    raise requests.RequestException(f"Failed after {retries} retries: {last_error}")


def get_cart_by_customer(customer_id):
    """Resolve cart_id from customer_id"""
    try:
        resp = request_with_retry("GET", f"{CART_SERVICE_URL}/carts/?customer_id={customer_id}")
        carts = resp.json() if isinstance(resp.json(), list) else []
        if carts:
            return carts[0].get("id")
    except Exception as exc:
        logger.error("Failed to resolve cart for customer %s: %s", customer_id, exc)
    return None


class OrderListCreateAPIView(APIView):
    def get(self, request):
        orders = Order.objects.all().order_by("-id")
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        """
        Orchestrate order creation with payment and shipment.
        
        Request body:
        {
            "customer_id": int,
            "cart_id": int,
            "payment_method": str,
            "shipping_method": str
        }
        """
        customer_id = request.data.get("customer_id")
        cart_id = request.data.get("cart_id")
        payment_method = request.data.get("payment_method", "CREDIT_CARD")
        shipping_method = request.data.get("shipping_method", "STANDARD")

        # Validation
        if not customer_id:
            logger.warning("Order creation failed: missing customer_id")
            return Response(
                {"detail": "customer_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not cart_id:
            logger.warning("Order creation failed: missing cart_id")
            return Response(
                {"detail": "cart_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch cart data
        try:
            logger.info("Fetching cart %s from cart service", cart_id)
            cart_resp = request_with_retry("GET", f"{CART_SERVICE_URL}/carts/{cart_id}/")
            if cart_resp.status_code >= 400:
                logger.error("Cart %s not found (status %s)", cart_id, cart_resp.status_code)
                return Response(
                    {"detail": "Cart not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except requests.RequestException as exc:
            logger.error("Cart service unreachable: %s", exc)
            return Response(
                {"detail": "Cart service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Fetch cart items
        try:
            logger.info("Fetching cart items for cart %s", cart_id)
            items_resp = request_with_retry("GET", f"{CART_SERVICE_URL}/cart-items/?cart_id={cart_id}")
            items = items_resp.json() if isinstance(items_resp.json(), list) else []
            
            if not items:
                logger.warning("Cart %s is empty", cart_id)
                return Response(
                    {"detail": "Cart is empty"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as exc:
            logger.error("Failed to fetch cart items: %s", exc)
            return Response(
                {"detail": "Failed to fetch cart items"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Validate stock before creating order
        stock_plan = []
        try:
            for item in items:
                book_id = item.get("book_id")
                quantity = int(item.get("quantity", 0))
                if not book_id or quantity <= 0:
                    return Response(
                        {"detail": "Invalid cart item payload"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                validate_resp = request_with_retry("GET", f"{BOOK_SERVICE_URL}/books/{book_id}/validate/")
                if validate_resp.status_code >= 400:
                    return Response(
                        {"detail": f"Book {book_id} not found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                validate_data = validate_resp.json() if validate_resp.content else {}
                stock = int(validate_data.get("stock", 0))
                if stock < quantity:
                    return Response(
                        {
                            "detail": f"Insufficient stock for book {book_id}",
                            "book_id": book_id,
                            "requested": quantity,
                            "available": stock,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                stock_plan.append(
                    {
                        "book_id": book_id,
                        "decrease_by": quantity,
                        "new_stock": stock - quantity,
                    }
                )
        except requests.RequestException as exc:
            logger.error("Book service unavailable while validating stock: %s", exc)
            return Response(
                {"detail": "Book service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Calculate total
        try:
            total = sum(
                Decimal(str(item.get("unit_price", 0))) * int(item.get("quantity", 0))
                for item in items
            )
            logger.info("Cart %s total calculated: %s", cart_id, total)
        except Exception as exc:
            logger.error("Failed to calculate total: %s", exc)
            return Response(
                {"detail": "Invalid cart item prices"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create order record
        try:
            order = Order.objects.create(
                customer_id=customer_id,
                cart_id=cart_id,
                total_amount=total,
                status="PENDING",
                payment_status="PENDING",
                shipment_status="PENDING",
            )
            logger.info("Order %s created (pending transaction)", order.id)
        except Exception as exc:
            logger.error("Failed to create order: %s", exc)
            return Response(
                {"detail": "Failed to create order"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Create order items
        try:
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    book_id=item.get("book_id"),
                    quantity=item.get("quantity", 1),
                    unit_price=item.get("unit_price", 0),
                )
            logger.info("Created %d order items for order %s", len(items), order.id)
        except Exception as exc:
            logger.error("Failed to create order items: %s", exc)
            order.delete()
            return Response(
                {"detail": "Failed to save order items"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Process payment
        pay_payload = {
            "order_id": order.id,
            "customer_id": customer_id,
            "amount": str(total),
            "payment_method": payment_method,
        }
        
        try:
            logger.info("Processing payment for order %s (amount=%s, method=%s)", 
                       order.id, total, payment_method)
            pay_resp = request_with_retry("POST", f"{PAY_SERVICE_URL}/payments/", pay_payload)
            order.payment_status = "PAID" if pay_resp.status_code < 400 else "FAILED"
            logger.info("Payment for order %s: %s (status=%s)", 
                       order.id, order.payment_status, pay_resp.status_code)
        except requests.RequestException as exc:
            logger.error("Payment service error for order %s: %s", order.id, exc)
            order.payment_status = "FAILED"

        # Deduct stock only when payment succeeds.
        if order.payment_status == "PAID":
            for plan in stock_plan:
                try:
                    update_resp = request_with_retry(
                        "PUT",
                        f"{BOOK_SERVICE_URL}/books/{plan['book_id']}/",
                        {"stock": plan["new_stock"]},
                    )
                    if update_resp.status_code >= 400:
                        logger.error(
                            "Failed to deduct stock for book %s (status=%s)",
                            plan["book_id"],
                            update_resp.status_code,
                        )
                        order.status = "PARTIAL"
                except requests.RequestException as exc:
                    logger.error("Failed to deduct stock for book %s: %s", plan["book_id"], exc)
                    order.status = "PARTIAL"

        # Process shipment
        ship_payload = {
            "order_id": order.id,
            "customer_id": customer_id,
            "address": "N/A",
            "shipping_method": shipping_method,
        }
        
        try:
            logger.info("Creating shipment for order %s (method=%s)", order.id, shipping_method)
            ship_resp = request_with_retry("POST", f"{SHIP_SERVICE_URL}/shipments/", ship_payload)
            order.shipment_status = "CREATED" if ship_resp.status_code < 400 else "FAILED"
            logger.info("Shipment for order %s: %s (status=%s)", 
                       order.id, order.shipment_status, ship_resp.status_code)
        except requests.RequestException as exc:
            logger.error("Shipment service error for order %s: %s", order.id, exc)
            order.shipment_status = "FAILED"

        # Determine final order status
        if order.payment_status == "PAID" and order.shipment_status == "CREATED":
            order.status = "COMPLETED"
        elif order.payment_status == "PAID" or order.shipment_status == "CREATED":
            order.status = "PARTIAL"
        else:
            order.status = "FAILED"

        order.save()

        logger.info("Order %s finalized: status=%s, payment=%s, shipment=%s",
                   order.id, order.status, order.payment_status, order.shipment_status)

        return Response(
            {
                "order_id": order.id,
                "status": order.status.lower(),
                "payment_status": order.payment_status.lower(),
                "shipment_status": order.shipment_status.lower(),
            },
            status=status.HTTP_201_CREATED,
        )
