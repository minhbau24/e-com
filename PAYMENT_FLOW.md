# Payment Flow Refactoring - No Checkout Page

## 📋 Overview

The system has been refactored to remove the intermediate checkout page. Payment flow now goes directly from Cart to Order Service orchestration.

**Old Flow:**
```
Cart → CheckoutPage (form) → /orders/ → Payment Service → Shipment Service
```

**New Flow:**
```
Cart → "Thanh toán" button → /orders/ → Order Service Orchestrates → Payment + Shipment
```

---

## 🔄 Business Flow (New)

### 1. User Action
- User clicks **"💳 Thanh toán"** button in Cart page
- System validates:
  - ✅ Cart has items
  - ✅ User is logged in
  - ✅ User has address

### 2. Frontend Request
```javascript
POST /orders/
Content-Type: application/json

{
  "customer_id": 2,
  "cart_id": 3,
  "address": "123 Nguyen Hue, HCM City",
  "payment_method": "CREDIT_CARD",
  "shipping_method": "STANDARD"
}
```

### 3. Order Service Orchestration

Order Service (`/orders/` POST handler) performs:

#### Step 1: Validation
- ✅ customer_id exists
- ✅ cart_id exists (or resolve from customer_id)
- ✅ cart has valid items with prices

#### Step 2: Create Order Record
```python
Order.objects.create(
    customer_id=customer_id,
    cart_id=cart_id,
    total_amount=calculated_total,
    status="PENDING",
    payment_status="PENDING",
    shipment_status="PENDING"
)
```

#### Step 3: Create Order Items
```python
for item in cart_items:
    OrderItem.objects.create(
        order=order,
        book_id=item.book_id,
        quantity=item.quantity,
        unit_price=item.unit_price
    )
```

#### Step 4: Call Payment Service
```
POST http://pay-service:8000/payments/

{
  "order_id": 123,
  "customer_id": 2,
  "amount": "250000",
  "payment_method": "CREDIT_CARD"
}
```

**Response:**
- ✅ Status 2xx → `payment_status = "PAID"`
- ❌ Status 4xx/5xx → `payment_status = "FAILED"`

#### Step 5: Call Shipment Service
```
POST http://ship-service:8000/shipments/

{
  "order_id": 123,
  "customer_id": 2,
  "address": "123 Nguyen Hue, HCM City",
  "shipping_method": "STANDARD"
}
```

**Response:**
- ✅ Status 2xx → `shipment_status = "CREATED"`
- ❌ Status 4xx/5xx → `shipment_status = "FAILED"`

#### Step 6: Determine Final Status

| Payment | Shipment | Order Status |
|---------|----------|--------------|
| PAID    | CREATED  | **COMPLETED** ✅ |
| PAID    | FAILED   | PARTIAL ⚠️    |
| FAILED  | CREATED  | PARTIAL ⚠️    |
| FAILED  | FAILED   | FAILED ❌     |

#### Step 7: Return Response
```json
{
  "id": 123,
  "customer_id": 2,
  "cart_id": 3,
  "total_amount": "250000.00",
  "status": "COMPLETED",
  "payment_status": "PAID",
  "shipment_status": "CREATED",
  "created_at": "2024-01-15T10:30:00Z",
  "items": [...]
}
```

### 4. Frontend Response Handling

**On Success:**
```
✅ Order #123 created successfully!
Payment: PAID
Shipment: CREATED

→ Redirect to home after 2 seconds → Clear cart
```

**On Error:**
```
❌ [Error message from backend]

Examples:
- ❌ customer_id is required
- ❌ No cart found for customer
- ❌ Cart is empty
- ❌ Cart service unavailable
- ❌ Payment service unavailable
```

---

## 🛠️ Technical Implementation

### Backend Changes

#### 1. Order Service Views (`order-service/core/views.py`)

**Enhanced Features:**
- ✅ Exponential backoff retry logic (2^attempt)
- ✅ Smart cart resolution (cart_id OR customer_id)
- ✅ Detailed logging at each step
- ✅ Comprehensive error handling
- ✅ Request timeout (5 seconds)
- ✅ Support for payment/shipping method parameters

**Key Functions:**

```python
def request_with_retry(method, url, payload=None, retries=3, base_delay=1):
    """Exponential backoff: 1s, 2s, 4s, 8s..."""
    # Retry on connection errors and 5xx server errors
    # Returns immediately on 4xx client errors
    
def get_cart_by_customer(customer_id):
    """Resolve cart_id from customer_id using cart service API"""
```

**Main Logic:**
```python
class OrderListCreateAPIView(APIView):
    def post(self, request):
        # 1. Validate inputs
        # 2. Resolve cart_id if needed
        # 3. Fetch cart and items
        # 4. Calculate total
        # 5. Create order + items
        # 6. Process payment (retry 3x)
        # 7. Process shipment (retry 3x)
        # 8. Update order status
        # 9. Log everything
        # 10. Return result
```

#### 2. Order Models (`order-service/core/models.py`)

**Updated Status Choices:**
```python
STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("COMPLETED", "Completed"),
    ("PARTIAL", "Partial"),
    ("FAILED", "Failed"),
]

PAYMENT_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("PAID", "Paid"),
    ("FAILED", "Failed"),
]

SHIPMENT_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("CREATED", "Created"),
    ("FAILED", "Failed"),
]
```

### Frontend Changes

#### 1. Cart Page (`storefront/src/pages/CartPage.jsx`)

**Old:**
```jsx
<Link className="btn btn-danger w-100 mt-3" to="/checkout">
  Go to checkout
</Link>
```

**New:**
```jsx
<button
  className="btn btn-danger w-100 mb-2"
  onClick={handlePayment}
  disabled={loading || !currentUser}
  style={{ fontSize: "16px", fontWeight: "bold" }}
>
  {loading ? "🔄 Processing..." : "💳 Thanh toán"}
</button>
```

**New Payment Handler:**
```javascript
const handlePayment = async () => {
  // 1. Validate cart & user
  // 2. Prepare order payload
  // 3. Call POST /orders/
  // 4. Show success message
  // 5. Redirect to home
  // 6. Clear cart
}
```

**Error Handling:**
- Shows error messages with ❌ emoji
- Displays required login message if not authenticated
- Disables button during processing

**Success Flow:**
- Shows ✅ Order ${id} confirmation
- Shows payment and shipment status
- Auto-redirects after 2 seconds
- Clears cart and localStorage

#### 2. App Props Update

CartPage now receives:
```jsx
<CartPage 
  cartItems={cartItems} 
  updateQty={updateQty} 
  removeItem={removeItem}
  currentUser={currentUser}              {/* NEW */}
  onCheckoutSuccess={onCheckoutSuccess}  {/* NEW */}
/>
```

### API Gateway

**Already Supports:**
```
POST /orders/ → proxies to POST order-service/orders/
GET /orders/ → proxies to GET order-service/orders/
```

No changes needed - already properly routing to Order Service.

---

## 📊 API Contract

### POST /orders/

**Request:**
```json
{
  "customer_id": 2,
  "cart_id": 3,
  "address": "123 Main St",
  "payment_method": "CREDIT_CARD",
  "shipping_method": "STANDARD"
}
```

**Required Fields:**
- `customer_id` (int) - Customer making the order

**Optional Fields:**
- `cart_id` (int) - Will be resolved from customer_id if not provided
- `address` (str) - Default: "N/A"
- `payment_method` (str) - Default: "CREDIT_CARD"
- `shipping_method` (str) - Default: "STANDARD"

**Response (201 Created):**
```json
{
  "id": 123,
  "customer_id": 2,
  "cart_id": 3,
  "total_amount": "250000.00",
  "status": "COMPLETED",
  "payment_status": "PAID",
  "shipment_status": "CREATED",
  "created_at": "2024-01-15T10:30:00Z",
  "items": [
    {
      "id": 401,
      "order": 123,
      "book_id": 1,
      "quantity": 2,
      "unit_price": "125000.00"
    }
  ]
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| 400  | Missing customer_id, Empty cart, Cart not found |
| 503  | Service unavailable (cart, payment, or shipment) |
| 500  | Order creation failure, Database error |

---

## 🔁 Retry Strategy

**Exponential Backoff:**
```
Attempt 1: Fail → Wait 1s → Retry
Attempt 2: Fail → Wait 2s → Retry
Attempt 3: Fail → Wait 4s → Retry
Attempt 4: Fail → Raise Exception
```

**Retry Trigger:**
- Connection errors (timeout, network error)
- Server errors (5xx status code)

**No Retry:**
- Client errors (4xx) - fail immediately
- Successful responses (2xx/3xx) - return immediately

---

## 📝 Logging

Every major step is logged with context:

```python
logger.info("Order %s created (pending transaction)", order.id)
logger.info("Fetching cart %s from cart service", cart_id)
logger.info("Processing payment for order %s (amount=%s, method=%s)", order.id, total, payment_method)
logger.info("Payment for order %s: %s (status=%s)", order.id, order.payment_status, pay_resp.status_code)
logger.info("Creating shipment for order %s (method=%s)", order.id, shipping_method)
logger.info("Order %s finalized: status=%s, payment=%s, shipment=%s", order.id, order.status, order.payment_status, order.shipment_status)
```

**Error Logging:**
```python
logger.error("Failed to resolve cart for customer %s: %s", customer_id, exc)
logger.error("Cart %s not found (status %s)", cart_id, cart_resp.status_code)
logger.error("Cart service unreachable: %s", exc)
logger.error("Payment service error for order %s: %s", order.id, exc)
```

---

## ⚠️ Key Differences from Old Flow

| Aspect | Old | New |
|--------|-----|-----|
| **Checkout Page** | ✅ Required form | ❌ Removed |
| **Guest Checkout** | ✅ Allowed (guest form) | ❌ Login required |
| **Direct Payment** | ❌ No | ✅ Yes (Cart → Payment) |
| **Cart Lookup** | Manual cart_id | Smart resolution |
| **Retry Logic** | Simple (fixed delay) | Exponential backoff |
| **Error Messages** | Generic | Detailed with context |
| **User Experience** | Multi-step | Direct checkout |

---

## 🚀 Testing Checklist

- [ ] User can add items to cart
- [ ] "Thanh toán" button appears when logged in
- [ ] Button is disabled when not logged in
- [ ] Loading indicator shows during payment
- [ ] Success message appears for completed orders
- [ ] Error messages show for validation/service failures
- [ ] Cart is cleared after successful checkout
- [ ] Page redirects to home after 2 seconds
- [ ] Order can be viewed in admin (GET /orders/)
- [ ] Payment service receives correct payload
- [ ] Shipment service receives correct payload

---

## 🐛 Troubleshooting

**Problem:** Button shows "Login to checkout →" even after login
- **Solution:** Clear browser cache, refresh page, check localStorage for jwt_token

**Problem:** "Cart service unavailable"
- **Solution:** Verify cart-service is running: `docker ps | grep cart`

**Problem:** Payment shows FAILED status
- **Solution:** Check pay-service logs: `docker logs pay-service`

**Problem:** Exponential backoff feels slow
- **Solution:** Adjust base_delay parameter in request_with_retry() - currently 1 second

---

## 📂 Files Modified

1. ✅ `order-service/core/views.py` - Enhanced orchestration logic
2. ✅ `order-service/core/models.py` - Added status choices
3. ✅ `storefront/src/pages/CartPage.jsx` - Added payment button & handler
4. ✅ `storefront/src/App.jsx` - Pass currentUser & onCheckoutSuccess to CartPage

## 📂 Files (Still Exist But Not Used)

1. `storefront/src/pages/CheckoutPage.jsx` - Can be removed in future cleanup
2. `/checkout` route in App.jsx - Can be removed in future cleanup

---

## 🎯 Next Steps (Optional)

1. Remove CheckoutPage.jsx and /checkout route
2. Add order history view (GET /orders/ with customer filter)
3. Add order details view (GET /orders/{id}/)
4. Add "Reorder" button on product detail
5. Add shipping address validation
6. Add different shipping methods (Express, Standard, Economy)
7. Add different payment methods (Visa, Mastercard, PayPal)
8. Add payment confirmation email
9. Add order status tracking
10. Add refund handling
