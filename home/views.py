import hmac
import json

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from account.cart_utils import add_product_to_cart, parse_quantity
from account.models import Order, Profile
from product.models import Product


def reply(text, contexts=None):
    payload = {"fulfillmentText": text}
    if contexts:
        payload["outputContexts"] = contexts
    return JsonResponse(payload)


def check_color_variant(product_name, color):
    product = Product.objects.filter(product_name__iexact=product_name).first()
    if product and product.color_variant.filter(color__iexact=color).exists():
        return True, product
    return False, None


def home_page(request):
    products = Product.objects.prefetch_related('product_images')
    return render(request, "home/index.html", {'products': products})


def search_page(request):
    query = (request.GET.get('q') or '').strip()

    if query:
        products = Product.objects.filter(
            Q(product_name__icontains=query) |
            Q(category__category_name__icontains=query) |
            Q(product_desc__icontains=query) |
            Q(price__icontains=query)
        ).distinct().prefetch_related('product_images')
    else:
        products = Product.objects.none()

    return render(request, 'home/search.html', {'products': products, 'query': query})


def add_to_cart_bot(user_profile, product_name, color_variant, quantity):
    product = Product.objects.filter(product_name__iexact=product_name).first()
    if product is None:
        return "The product does not exist."
    if not color_variant and product.color_variant.exists():
        return "Please select a color."

    item, error = add_product_to_cart(
        user_profile, product, quantity=parse_quantity(quantity), color_name=color_variant,
    )
    if error:
        return error
    return (f"{item.quantity} {product_name}(s) in your cart"
            f"{' (' + color_variant + ')' if color_variant else ''}! "
            f"How can I further assist you? You can say 'New order' or 'Track order'.")


def _find_param(data, key):
    """Look a parameter up in all output contexts (their order is not guaranteed)."""
    for ctx in data.get('queryResult', {}).get('outputContexts', []):
        value = ctx.get('parameters', {}).get(key)
        if value not in (None, ''):
            return value
    return None


@csrf_exempt
def handle_request(request):
    if request.method != "POST":
        return reply("Invalid request method.")

    # Optional shared secret so that not just anybody can call the webhook
    token = settings.DIALOGFLOW_WEBHOOK_TOKEN
    if token and not hmac.compare_digest(request.headers.get('X-Webhook-Token', ''), token):
        return JsonResponse({"fulfillmentText": "Unauthorized."}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return reply("Could not process the request.")

    query_result = data.get('queryResult', {})
    params = query_result.get('parameters', {})
    intent_name = query_result.get('intent', {}).get('displayName')
    session = data.get('session', '')  # projects/<project>/agent/sessions/<id>

    def ctx(name, lifespan, **parameters):
        c = {"name": f"{session}/contexts/{name}", "lifespanCount": lifespan}
        if parameters:
            c["parameters"] = parameters
        return c

    if intent_name == "track order:ongoing":
        order_id = params.get('order_id')
        if not order_id:
            return reply("Order ID not provided.")
        order = Order.objects.filter(order_id=order_id).first()
        if order is None:
            return reply(f"Order with ID {order_id} does not exist.")
        if order.status == "Delivered":
            return reply(f"Your order {order_id} has been delivered.")
        if order.status == "Processing":
            return reply(f"Your order {order_id} is currently being processed.")
        return reply(f"Your order {order_id} is in {order.status} state.")

    elif intent_name == "search.add-order":
        product_name = params.get('product')
        if not product_name:
            return reply("Please specify what you want to order.")

        products = Product.objects.filter(
            Q(product_name__icontains=product_name) |
            Q(category__category_name__icontains=product_name)
        ).distinct()
        count = products.count()

        if count > 1:
            names = ", ".join(p.product_name for p in products)
            return reply(f"Multiple products found: {names}. Can you be more specific?")
        if count == 1:
            product = products.first()
            return reply(
                f"{product.product_name} found. What color and quantity would you like?",
                [ctx("ongoing-add-order", 5, product_name=product.product_name),
                 ctx("ongoing-new-order", 0)],
            )
        return reply(f"Sorry, no product found for {product_name}.")

    elif intent_name == "new-order:color-quantity":
        color = params.get('color')
        quantity = params.get('quantity')
        product_name = _find_param(data, 'product_name')

        if not (product_name and color and quantity):
            return reply("Please specify the product color along with the quantity you want to add to the cart.")
        try:
            quantity = int(float(quantity))
            if quantity < 1:
                raise ValueError
        except (ValueError, TypeError):
            return reply("Please specify a valid quantity.")

        color_exists, _ = check_color_variant(product_name, color)
        if not color_exists:
            return reply(f"Sorry, {color} is not available for {product_name}.")

        return reply(
            f"To add {quantity} {product_name}(s) of color {color}, you first need to provide your email.",
            [ctx("ongoing-order-email", 5, product_name=product_name, color=color, quantity=quantity),
             ctx("ongoing-add-order", 0)],
        )

    elif intent_name == "new-order:email":
        email = params.get('email')
        product_name = _find_param(data, 'product_name')
        color = _find_param(data, 'color')
        quantity = _find_param(data, 'quantity')

        if not (email and product_name and color and quantity):
            return reply("Please provide a valid email address.")

        user_profile = Profile.objects.filter(user__email__iexact=email).first()
        if user_profile is None:
            return reply("We could not find a user with that email. Please try again.")

        result = add_to_cart_bot(user_profile, product_name, color, quantity)
        return reply(result, [ctx("ongoing-order-email", 0)])

    return reply("Intent not recognized.")