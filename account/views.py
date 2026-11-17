from django.urls import reverse
import stripe
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_POST
import datetime
import random

from .models import Profile, Cart, cartItems, Coupon, Order, OrderItem
from .cart_utils import get_profile, add_from_request, safe_back


def generate_custom_order_id():
    now = datetime.datetime.now()
    while True:
        order_id = f"ORD{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}{random.randint(100, 999)}"
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id
        now = datetime.datetime.now()


def login_page(request):
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password')

        user = User.objects.filter(username__iexact=email).first()
        if user is None:
            messages.warning(request, "You do not have an account.")
            return HttpResponseRedirect(request.path_info)

        profile = get_profile(user)
        if not profile.is_email_verified:
            messages.warning(request, "Your email is not verified.")
            return HttpResponseRedirect(request.path_info)

        user_obj = authenticate(username=user.username, password=password)
        if user_obj:
            login(request, user_obj)
            return redirect('/')

        messages.warning(request, "Invalid Credentials.")
        return HttpResponseRedirect(request.path_info)

    return render(request, 'account/login.html')


def register_page(request):
    if request.method == 'POST':
        firstname = (request.POST.get('firstname') or '').strip()
        lastname = (request.POST.get('lastname') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''

        if User.objects.filter(username__iexact=email).exists():
            messages.warning(request, "An account already exists with this email.")
            return HttpResponseRedirect(request.path_info)

        try:
            validate_password(password)
        except ValidationError as e:
            for err in e.messages:
                messages.warning(request, err)
            return HttpResponseRedirect(request.path_info)

        # create_user hashes the password; the post_save signal creates the Profile and sends the e-mail
        User.objects.create_user(first_name=firstname, last_name=lastname,
                                 email=email, username=email, password=password)
        messages.success(request, "Registration successful. An email has been sent.")
        return HttpResponseRedirect(request.path_info)

    return render(request, 'account/register.html')


def logout_view(request):
    logout(request)
    return redirect('/')


def activate_email(request, email_token):
    profile = Profile.objects.filter(email_token=email_token).first()
    if profile is None:
        return HttpResponse("Invalid email token. Email can't be verified.")
    profile.is_email_verified = True
    profile.save()
    messages.success(request, "Email verified. You can now sign in.")
    return redirect('login')


def cart_view(request):
    if not request.user.is_authenticated:
        messages.info(request, "You need to be logged in to view the cart.")
        return redirect('login')

    user_profile = get_profile(request.user)
    cart = Cart.objects.filter(is_paid=False, user=user_profile).first()

    if request.method == "POST":
        code = (request.POST.get('coupon') or '').strip()
        if cart is None or not cart.cart_items.exists():
            messages.info(request, "Your cart is empty.")
        elif not code:
            messages.info(request, "Please enter a coupon code.")
        else:
            coupon_obj = Coupon.objects.filter(coupon_code__iexact=code).first()
            if coupon_obj is None:
                messages.info(request, "Coupon Does not Exist.")
            elif coupon_obj.is_expired:
                messages.warning(request, "Coupon has Expired")
            elif cart.coupon:
                messages.info(request, "Coupon already Used.")
            elif cart.get_subtotal() < coupon_obj.minimum_amount:
                messages.info(request, f"Amount should reach \u20b9{coupon_obj.minimum_amount}")
            else:
                cart.coupon = coupon_obj
                cart.save()
                messages.success(request, "Coupon Applied.")
        return redirect('cart_view')

    cart_items_with_images = []
    if cart:
        items = cart.cart_items.select_related('product', 'color_variant', 'size_variant')
        for item in items:
            product_image = None
            if item.product:
                images = item.product.product_images
                if item.color_variant:
                    product_image = images.filter(color=item.color_variant).first()
                product_image = product_image or images.first()
            cart_items_with_images.append({
                'item': item,
                'image_url': product_image.image.url if product_image else None,
            })

    return render(request, 'account/cart.html', {
        'cart': cart,
        'cart_items_with_images': cart_items_with_images,
    })


@login_required
def remove_item(request, uid):
    # Only the owner can remove an item
    cartItems.objects.filter(uid=uid, cart__user__user=request.user, cart__is_paid=False).delete()
    return safe_back(request, fallback='cart_view')


@login_required
def remove_coupon(request, uid):
    cart = Cart.objects.filter(uid=uid, user__user=request.user, is_paid=False).first()
    if cart:
        cart.coupon = None
        cart.save()
        messages.info(request, "Coupon removed.")
    return safe_back(request, fallback='cart_view')


@login_required
@require_POST
def checkout_session(request, uid):
    cart = get_object_or_404(Cart, uid=uid, user__user=request.user, is_paid=False)
    cart_items = list(cart.cart_items.select_related('product', 'color_variant', 'size_variant'))
    cart_items = [i for i in cart_items if i.product]  # skip items whose product was deleted

    if not cart_items:
        messages.info(request, "Your cart is empty.")
        return redirect('cart_view')
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Payments are not configured yet (missing STRIPE_SECRET_KEY).")
        return redirect('cart_view')

    stripe.api_key = settings.STRIPE_SECRET_KEY

    line_items = []
    for item in cart_items:
        color = item.color_variant.color if item.color_variant else "No color"
        size = item.size_variant.size if item.size_variant else "No size"
        line_items.append({
            "price_data": {
                "currency": "inr",
                "unit_amount": int(item.get_unit_price() * 100),  # paise
                "product_data": {
                    "name": item.product.product_name,
                    "description": f"Color: {color}, Size: {size}",
                },
            },
            "quantity": item.quantity,
        })

    # The coupon discount must also be applied to what Stripe actually charges
    extra = {}
    discount = cart.get_discount()
    try:
        if discount > 0:
            stripe_coupon = stripe.Coupon.create(
                amount_off=int(discount * 100), currency="inr", duration="once",
                name=cart.coupon.coupon_code,
            )
            extra["discounts"] = [{"coupon": stripe_coupon.id}]

        success_url = request.build_absolute_uri(reverse('success_url', kwargs={'uid': uid}))
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            metadata={"cart_id": str(uid)},
            mode="payment",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse('cancel_url')),
            **extra,
        )
    except stripe.StripeError as e:
        messages.error(request, f"Could not start the payment: {getattr(e, 'user_message', None) or 'please try again.'}")
        return redirect('cart_view')

    return redirect(session.url)


@login_required
def buy_now(request, slug):
    if add_from_request(request, slug):
        return redirect('cart_view')
    return safe_back(request, fallback='home_page')


@login_required
def success_view(request, uid):
    cart = get_object_or_404(Cart, uid=uid, user__user=request.user)

    # Never trust the URL alone: confirm with Stripe that this cart was really paid
    session_id = request.GET.get('session_id')
    paid = False
    if session_id and settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            paid = (session.payment_status == "paid"
                    and (session.metadata or {}).get("cart_id") == str(cart.uid))
        except stripe.StripeError:
            paid = False
    if not paid:
        messages.warning(request, "We could not confirm your payment.")
        return redirect('cart_view')

    with transaction.atomic():
        # Reloading this page must not create duplicate orders
        if not Order.objects.filter(cart=cart).exists():
            cart.is_paid = True
            cart.save()
            order = Order.objects.create(
                user=cart.user, cart=cart,
                order_id=generate_custom_order_id(), status="Processing",
            )
            for item in cart.cart_items.all():
                OrderItem.objects.create(
                    order=order, product=item.product,
                    color_variant=item.color_variant, size_variant=item.size_variant,
                    quantity=item.quantity,
                )

    return render(request, 'base/success.html')


@login_required
def my_orders_view(request):
    profile = get_profile(request.user)
    orders = (Order.objects.filter(user=profile)
              .prefetch_related('order_items__product', 'order_items__color_variant', 'order_items__size_variant')
              .order_by('-created_at'))
    return render(request, 'account/my_orders.html', {'orders': orders})