from django.urls import path
from . import views

app_name = 'flowfinds'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('p/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<str:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<str:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout_create_order, name='checkout'),
    path('payment/<str:order_id>/', views.payment_stub, name='payment_stub'),
    path('admin/add-product/', views.admin_add_product, name='admin_add_product'),
    path('checkout/address/', views.checkout_address, name='checkout_address'),
    path('admin/orders/', views.admin_orders_list, name='admin_orders'),
    path('admin/orders/<str:order_id>/', views.admin_order_detail, name='admin_order_detail'),
]
