<div align="center">

# 🛒 Django E-commerce Store with AI Chatbot

**A full-stack e-commerce platform built with Django, featuring email-verified accounts, Stripe payments, coupons, PDF invoices, and a Dialogflow chatbot that tracks orders and adds products to your cart from plain text.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-Payments-635BFF?logo=stripe&logoColor=white)
![Dialogflow](https://img.shields.io/badge/Dialogflow-Chatbot-FF9800?logo=dialogflow&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-4-7952B3?logo=bootstrap&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)

</div>

---

## 📖 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Running with Docker](#-running-with-docker)
- [Stripe Test Payments](#-stripe-test-payments)
- [Chatbot Setup (Dialogflow)](#-chatbot-setup-dialogflow)
- [Routes](#-routes)
- [Data Models](#-data-models)
- [Screenshots](#-screenshots)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)

---

## ✨ Features

| Area | What you get |
|---|---|
| 🔐 **Authentication** | Registration and login with **email verification** (activation link sent via SMTP) |
| 🛍️ **Catalog** | Categories, products, image galleries, color and size variants with variant pricing |
| 🔎 **Search** | Search products by name from the navbar |
| 🧺 **Cart** | Add/remove items, live cart counter, per-variant pricing, quantity support |
| 🎟️ **Coupons** | Apply/remove discount codes with a minimum cart amount rule |
| 💳 **Payments** | Secure checkout through **Stripe Checkout**, plus a one-click **Buy Now** flow |
| 📦 **Orders** | Order history page with order IDs and status |
| 🧾 **Invoices** | PDF invoice generation (xhtml2pdf / ReportLab) |
| 🤖 **AI Chatbot** | Dialogflow assistant that can **track an order by ID** and **add products to your cart** from natural language |
| 🛠️ **Admin panel** | Manage products, categories, variants, coupons, carts and orders via Django Admin |
| 📱 **Responsive UI** | Bootstrap-based layout that works on desktop and mobile |

---

## 🧰 Tech Stack

- **Backend:** Python 3.12, Django 5.0
- **Database:** SQLite (development) – easily swappable for PostgreSQL
- **Payments:** Stripe (`stripe` Python SDK)
- **Chatbot:** Google Dialogflow + Django webhook
- **Email:** Django SMTP backend (Gmail by default)
- **PDF:** xhtml2pdf, ReportLab
- **Frontend:** Django templates, Bootstrap, jQuery, HTMX, Font Awesome
- **Config:** `python-decouple` for environment variables
- **DevOps:** Docker

---

## 🗂️ Project Structure

```
My_ecommerce_store/
├── account/          # Auth, profile, cart, coupons, orders, Stripe checkout
├── product/          # Category, Product, variants, product images
├── home/             # Home page, search, Dialogflow webhook (handle-request)
├── base/             # Shared BaseModel, email helpers
├── ecommerce/        # Project settings, URLs, WSGI/ASGI
├── templates/        # HTML templates (account, home, products, pdf, base)
├── public/static/    # CSS, JS, fonts, images, product media
├── Dockerfile
├── requirements.txt
└── manage.py
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ (3.12 recommended)
- `pip`
- A [Stripe](https://stripe.com) account (test mode is fine)
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) for sending emails

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/django-ecommerce-chatbot.git
cd django-ecommerce-chatbot
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root (see [Environment Variables](#-environment-variables)).

### 5. Create and apply database migrations

> Migration files are excluded in `.gitignore`, so generate them first.

```bash
python manage.py makemigrations base product account home
python manage.py migrate
```

### 6. Create an admin user

```bash
python manage.py createsuperuser
```

### 7. Run the server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** for the store and **http://127.0.0.1:8000/admin/** for the admin panel.

### 8. Add sample data

In the admin panel, create a **Category**, some **Colors/Sizes**, a **Product** with images, and a **Coupon** so you can test the full shopping flow.

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
# Stripe
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx

# Email (Gmail SMTP)
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
```

> ⚠️ Never commit your `.env` file. It is already listed in `.gitignore`.

---

## 🐳 Running with Docker

```bash
# Make sure your .env file exists first
docker build -t django-ecommerce .
docker run -p 8000:8000 django-ecommerce
```

Then visit **http://localhost:8000**.

---

## 💳 Stripe Test Payments

Use Stripe's test card to simulate a successful payment:

| Field | Value |
|---|---|
| Card number | `4242 4242 4242 4242` |
| Expiry | Any future date (e.g. `12/34`) |
| CVC | Any 3 digits (e.g. `567`) |
| Name / ZIP | Any |

---

## 🤖 Chatbot Setup (Dialogflow)

The chatbot talks to Django through a webhook at `/handle-request/`.

1. Create an agent in the [Dialogflow Console](https://dialogflow.cloud.google.com/).
2. Create intents for **order tracking** and **add to cart**.
3. Enable **Fulfillment → Webhook** and point it to your public URL:
   ```
   https://<your-domain-or-ngrok-url>/handle-request/
   ```
4. For local testing, expose your server with [ngrok](https://ngrok.com/):
   ```bash
   ngrok http 8000
   ```
5. Embed the Dialogflow Messenger snippet in `templates/base/base.html` with your own agent ID.

**Example conversations**

- *"Where is my order ORD123?"* → returns the order status
- *"Add 2 black iPhone 14 Pro to my cart"* → finds the product and adds it to the cart

---

## 🧭 Routes

| Route | Description |
|---|---|
| `/` | Home page |
| `/search/` | Product search |
| `/product/<slug>/` | Product detail page |
| `/account/register/` | Create an account |
| `/account/login/` | Log in |
| `/account/activate/<token>` | Verify email |
| `/account/cart-view/` | View cart |
| `/account/add-to-cart/<slug>` | Add product to cart |
| `/account/buy_now/<slug>` | Buy a product instantly |
| `/account/checkout_session/<uid>` | Start Stripe checkout |
| `/account/my-orders/` | Order history |
| `/handle-request/` | Dialogflow webhook |
| `/admin/` | Django admin |

---

## 🗃️ Data Models

```
User ──1:1── Profile ──1:N── Cart ──1:N── cartItems ──► Product / ColorVariant / SizeVariant
                  │              └── Coupon (optional)
                  └──1:N── Order ──1:N── OrderItem

Category ──1:N── Product ──1:N── ProductImage
Product ──M:N── ColorVariant, SizeVariant
```

---

## 📸 Screenshots

> Add your own screenshots to a `docs/screenshots/` folder and reference them here.

| Home | Product | Cart |
|---|---|---|
| ![Home](docs/screenshots/home.png) | ![Product](docs/screenshots/product.png) | ![Cart](docs/screenshots/cart.png) |

| Checkout | Orders | Chatbot |
|---|---|---|
| ![Checkout](docs/screenshots/checkout.png) | ![Orders](docs/screenshots/orders.png) | ![Chatbot](docs/screenshots/chatbot.png) |

---

## 🗺️ Roadmap

- [ ] Stripe webhooks for reliable payment confirmation
- [ ] Product reviews and ratings
- [ ] Wishlist
- [ ] Order status updates by email
- [ ] PostgreSQL + production settings (`DEBUG=False`, `ALLOWED_HOSTS`)
- [ ] Automated tests and CI

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m "Add amazing feature"`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

<div align="center">

⭐ If you found this project useful, please consider giving it a star!

</div>