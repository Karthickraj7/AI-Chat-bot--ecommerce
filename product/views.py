from django.shortcuts import get_object_or_404, redirect, render

from account.cart_utils import add_from_request, safe_back
from .models import ColorVariant, Product


def get_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    context = {'product': product}

    size = request.GET.get('size')
    if size:
        price = product.get_product_price_by_size(size)
        if price is not None:
            context['updated_price'] = price
            context['selected_size'] = size

    product_images = product.product_images.all()
    color = request.GET.get('color')
    if color:
        selected_color_variant = ColorVariant.objects.filter(color=color).first()
        if selected_color_variant:
            context['selected_color'] = color
            filtered = product.product_images.filter(color=selected_color_variant)
            product_images = filtered or product_images  # fall back if no image for that color
    context['product_images'] = product_images

    return render(request, "products/product.html", context=context)


def add_to_cart(request, slug):
    ok = add_from_request(request, slug)
    if not ok and not request.user.is_authenticated:
        return redirect('login')
    return safe_back(request, fallback='home_page')