from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from product.models import Product
from .models import Profile, Cart, cartItems

MAX_QUANTITY = 100


def get_profile(user):
    if not user.is_authenticated:
        return None
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def parse_quantity(raw):
    try:
        qty = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, min(qty, MAX_QUANTITY))


def add_product_to_cart(profile, product, quantity=1, color_name=None, size_name=None):
    """
    Adds a product to the user's open cart (merging with an identical line item).
    Returns (cart_item, error_message). Nothing is written when there is an error.
    """
    color = size = None

    if color_name:
        color = product.color_variant.filter(color__iexact=color_name).first()
        if color is None:
            return None, "The selected color is not available."
    elif product.color_variant.exists():
        return None, "Please select a color."

    if size_name:
        size = product.size_variant.filter(size=size_name).first()
        if size is None:
            return None, "The selected size is not available."

    cart = Cart.objects.filter(user=profile, is_paid=False).first()
    if cart is None:
        cart = Cart.objects.create(user=profile)

    item = cartItems.objects.filter(
        cart=cart, product=product, color_variant=color, size_variant=size
    ).first()
    if item:
        item.quantity = min(item.quantity + quantity, MAX_QUANTITY)
        item.save()
    else:
        item = cartItems.objects.create(
            cart=cart, product=product, color_variant=color,
            size_variant=size, quantity=quantity,
        )
    return item, None


def add_from_request(request, slug):
    """Shared logic of 'Add to cart' and 'Buy now'. Returns True on success."""
    profile = get_profile(request.user)
    if profile is None:
        messages.info(request, "You need to be logged in to add items to the cart.")
        return False
    product = Product.objects.filter(slug=slug).first()
    if product is None:
        messages.error(request, "That product does not exist.")
        return False

    _, error = add_product_to_cart(
        profile,
        product,
        quantity=parse_quantity(request.GET.get('quantity')),
        color_name=request.GET.get('color_variant'),
        size_name=request.GET.get('size_variant'),
    )
    if error:
        messages.error(request, error)
        return False
    return True


def safe_back(request, fallback='home_page'):
    """Redirect to the previous page only if it is on this site (and exists)."""
    ref = request.META.get('HTTP_REFERER')
    if ref and url_has_allowed_host_and_scheme(ref, allowed_hosts={request.get_host()}):
        return redirect(ref)
    return redirect(fallback)