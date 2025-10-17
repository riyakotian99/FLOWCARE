from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from decimal import Decimal
from .models import Product, Order, OrderItem
from .forms import ProductForm, AddressForm
import json
from .models import OrderRecord  # Django model (mirror)
from django.contrib.auth import get_user_model

def product_list(request):
    products = Product.objects.filter(active=True)
    return render(request, 'flowfinds/product_list.html', {'products': products})


def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    return render(request, 'flowfinds/product_detail.html', {'product': product})


def _get_cart(request):
    return request.session.setdefault('flowfinds_cart', {})


def add_to_cart(request, product_id):
    if request.method != 'POST':
        return redirect('flowfinds:product_list')
    cart = _get_cart(request)
    qty = int(request.POST.get('quantity', 1))
    cart[str(product_id)] = cart.get(str(product_id), 0) + qty
    request.session.modified = True
    return redirect('flowfinds:cart_detail')


def cart_detail(request):
    cart = _get_cart(request)
    items = []
    total = Decimal('0.00')
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=pid)
        except Product.DoesNotExist:
            continue
        line_total = p.price * int(qty)
        total += line_total
        items.append({'product': p, 'qty': int(qty), 'line_total': line_total})
    return render(request, 'flowfinds/cart_detail.html', {'items': items, 'total': total})


def remove_from_cart(request, product_id):
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    request.session.modified = True
    return redirect('flowfinds:cart_detail')


@login_required
def checkout_create_order(request):
    """
    When user clicks Checkout, redirect to the address form page.
    """
    cart = _get_cart(request)
    if not cart:
        return redirect('flowfinds:product_list')
    return redirect('flowfinds:checkout_address')


@login_required
def checkout_address(request):
    """
    Show address form. On POST, create Order with address and Cash on Delivery.
    Then clear the cart and redirect to payment_stub which will show the confirmation.
    """
    cart = _get_cart(request)
    if not cart:
        return redirect('flowfinds:product_list')

    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            order_items = []
            total = Decimal('0.00')
            for pid, qty in cart.items():
                try:
                    p = Product.objects.get(id=pid)
                except Product.DoesNotExist:
                    continue
                order_items.append(OrderItem(
                    product_id=str(p.id),
                    title=p.title,
                    price=p.price,
                    quantity=int(qty),
                    image_url=getattr(p, 'image_url', '')
                ))
                total += p.price * int(qty)

            # create order and set payment to Cash on Delivery
            order = Order(
                user_id=str(request.user.pk),
                items=order_items,
                total=total,
                # set status to 'paid' if you want the immediate confirmed UI; 
                # change to 'pending' if you'd like staff to mark paid later.
                status='paid',
                payment_id='Cash on Delivery',
                recipient_name=form.cleaned_data['recipient_name'],
                phone=form.cleaned_data['phone'],
                address_line1=form.cleaned_data['address_line1'],
                address_line2=form.cleaned_data.get('address_line2', ''),
                city=form.cleaned_data['city'],
                state=form.cleaned_data['state'],
                pincode=form.cleaned_data['pincode'],
                country=form.cleaned_data['country'],
                delivery_instructions=form.cleaned_data.get('delivery_instructions', '')
            )
                        # save the MongoEngine order
            order.save()

            # --- Mirror into Django ORM OrderRecord for admin visibility ---
            try:
                items_for_record = []
                for it in order_items:
                    items_for_record.append({
                        "product_id": it.product_id,
                        "title": it.title,
                        "price": str(it.price),   # convert Decimal to string for JSON safety
                        "quantity": int(it.quantity),
                        "image_url": getattr(it, 'image_url', '')
                    })

                django_user = None
                try:
                    if request.user and request.user.is_authenticated:
                        django_user = request.user
                except Exception:
                    django_user = None

                OrderRecord.objects.create(
                    mongo_order_id=str(order.pk),
                    user=django_user,
                    total=total,
                    status=order.status or '',
                    payment_id=order.payment_id or '',
                    recipient_name=order.recipient_name or '',
                    phone=order.phone or '',
                    address_line1=order.address_line1 or '',
                    address_line2=order.address_line2 or '',
                    city=order.city or '',
                    state=order.state or '',
                    pincode=order.pincode or '',
                    country=order.country or '',
                    delivery_instructions=order.delivery_instructions or '',
                    items_json=json.dumps(items_for_record)
                )
            except Exception as e:
                # do not interrupt the user flow if mirroring fails; log to console for debugging
                print("Warning: failed to create OrderRecord mirror:", e)

            # clear session cart and redirect to confirmation (payment_stub will render confirmed)
            request.session['flowfinds_cart'] = {}
            return redirect('flowfinds:payment_stub', order_id=str(order.pk))

    else:
        form = AddressForm()

    # optionally, you might want to pass cart summary to the template
    # to show items on the address page. For now we pass cart dictionary.
    return render(request, 'flowfinds/checkout_address.html', {'form': form, 'cart': cart})


@login_required
def payment_stub(request, order_id):
    """
    If order has Cash on Delivery or status 'paid', render confirmed view immediately.
    Otherwise, fallback to original payment POST flow (kept for compatibility).
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return redirect('flowfinds:product_list')

    # If order looks like COD or is already paid -> show confirmation
    if (order.payment_id and 'cash' in order.payment_id.lower()) or order.status == 'paid':
        return render(request, 'flowfinds/payment_stub.html', {
            'order': order,
            'confirmed': True,
            'payment_mode': order.payment_id or 'Cash on Delivery'
        })

    # Otherwise preserve original form POST for alternate payment modes (not used currently)
    if request.method == "POST":
        payment_mode = request.POST.get('payment_mode', '').strip()
        if not payment_mode:
            return render(request, 'flowfinds/payment_stub.html', {'order': order, 'confirmed': False})

        order.status = 'paid'
        order.payment_id = payment_mode
        order.save()

        return render(request, 'flowfinds/payment_stub.html', {
            'order': order,
            'confirmed': True,
            'payment_mode': payment_mode
        })

    # GET: show payment options (shouldn't be used in COD flow)
    return render(request, 'flowfinds/payment_stub.html', {'order': order, 'confirmed': False})


@staff_member_required
def admin_add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            image_url = ''
            if request.FILES.get('image'):
                f = request.FILES['image']
                path = default_storage.save(f'flowfinds/products/{f.name}', ContentFile(f.read()))
                image_url = default_storage.url(path)
            p = Product(
                title=form.cleaned_data['title'],
                slug=form.cleaned_data['slug'],
                description=form.cleaned_data['description'],
                price=form.cleaned_data['price'],
                stock=form.cleaned_data['stock'],
                image_url=image_url,
                active=form.cleaned_data.get('active', False)
            )
            p.save()
            return redirect('flowfinds:product_list')
    else:
        form = ProductForm()
    return render(request, 'flowfinds/admin_add_product.html', {'form': form})


# -------------------------
# Staff-only simple order admin pages
# -------------------------
@staff_member_required
def admin_orders_list(request):
    orders = Order.objects.order_by('-created_at')[:200]
    return render(request, 'flowfinds/admin_orders.html', {'orders': orders})


@staff_member_required
def admin_order_detail(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return redirect('flowfinds:admin_orders')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ('pending', 'paid', 'shipped', 'cancelled'):
            order.status = new_status
            order.save()

    return render(request, 'flowfinds/admin_order_detail.html', {'order': order})
