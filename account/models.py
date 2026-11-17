from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from base.emails import send_account_activation_email
from base.models import BaseModel
from django.db.models.signals import post_save
import uuid
from product.models import Product, ColorVariant, SizeVariant, ProductImage


class Coupon(BaseModel):
    coupon_code = models.CharField(max_length=10)
    is_expired = models.BooleanField(default=False)
    discount_price = models.IntegerField(default=1000)
    minimum_amount = models.IntegerField(default=7000)

    def __str__(self) -> str:
        return self.coupon_code


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_email_verified = models.BooleanField(default=False)
    email_token = models.CharField(max_length=100, null=True, blank=True)
    profile_img = models.ImageField(upload_to="profile", blank=True)

    def __str__(self) -> str:
        return f"{self.user.first_name} {self.user.last_name}"

    def get_cart_count(self):
        return cartItems.objects.filter(cart__user=self, cart__is_paid=False).count()


class Cart(BaseModel):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='carts')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user.user.first_name} {self.user.user.last_name}"

    def get_subtotal(self):
        return sum(item.get_cartitem_price() for item in self.cart_items.all())

    def get_discount(self):
        """Discount actually applicable right now (0 if coupon is missing, expired or below minimum)."""
        total = self.get_subtotal()
        coupon = self.coupon
        if coupon and not coupon.is_expired and total >= coupon.minimum_amount:
            return min(coupon.discount_price, total)  # never go negative
        return 0

    def get_cart_price(self):
        return self.get_subtotal() - self.get_discount()


class cartItems(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    color_variant = models.ForeignKey(ColorVariant, on_delete=models.SET_NULL, null=True, blank=True)
    size_variant = models.ForeignKey(SizeVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1)

    def __str__(self) -> str:
        name = self.product.product_name if self.product else "Deleted product"
        return f"{name}-{self.cart.user.user.email}"

    def get_unit_price(self):
        if not self.product:
            return 0
        price = self.product.price
        if self.size_variant:
            price += self.size_variant.price
        return price

    def get_cartitem_price(self):
        return self.get_unit_price() * self.quantity


class Order(BaseModel):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="orders")
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, default="Processing")

    def __str__(self):
        return f"Order {self.order_id} for {self.user.user.email}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    color_variant = models.ForeignKey(ColorVariant, on_delete=models.SET_NULL, null=True, blank=True)
    size_variant = models.ForeignKey(SizeVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        name = self.product.product_name if self.product else "Deleted product"
        return f"{name} - {self.quantity} pcs"


# Creates a Profile for every new User and sends the activation e-mail.
@receiver(post_save, sender=User)
def send_email_token(sender, instance, created, **kwargs):
    if not created:
        return
    email_token = str(uuid.uuid4())
    Profile.objects.create(user=instance, email_token=email_token)
    # A mail failure (bad SMTP settings, empty e-mail on createsuperuser) must not break user creation
    if instance.email:
        try:
            send_account_activation_email(instance.email, email_token)
        except Exception as e:
            print("Could not send activation e-mail:", e)