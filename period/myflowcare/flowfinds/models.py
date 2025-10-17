# flowfinds/models.py

from mongoengine import Document, EmbeddedDocument, fields, NULLIFY
import datetime

# Django ORM alias import (you already had this in your file)
from django.db import models as djmodels
from django.conf import settings
from django.utils import timezone
import json


class Category(Document):
    name = fields.StringField(max_length=100, required=True)
    slug = fields.StringField(max_length=150, required=True, unique=True)
    meta = {'collection': 'flowfinds_categories', 'indexes': ['slug']}


class Product(Document):
    category = fields.ReferenceField(Category, required=False, reverse_delete_rule=NULLIFY)
    title = fields.StringField(required=True, max_length=200)
    slug = fields.StringField(required=True, unique=True)
    description = fields.StringField()
    price = fields.DecimalField(required=True, precision=2)
    stock = fields.IntField(default=0)
    image_url = fields.StringField()  # store MEDIA URL or CDN path
    active = fields.BooleanField(default=True)
    created_at = fields.DateTimeField(default=datetime.datetime.utcnow)
    meta = {'collection': 'flowfinds_products', 'indexes': ['slug', 'title']}


class OrderItem(EmbeddedDocument):
    product_id = fields.StringField(required=True)
    title = fields.StringField()
    price = fields.DecimalField(precision=2)
    quantity = fields.IntField(default=1)
    image_url = fields.StringField()


class Order(Document):
    user_id = fields.StringField()  # store Django user pk as string
    items = fields.EmbeddedDocumentListField(OrderItem)
    total = fields.DecimalField(precision=2, default=0)

    # payment & status
    status = fields.StringField(choices=('pending', 'paid', 'shipped', 'cancelled'), default='pending')
    payment_id = fields.StringField()   # gateway txn id or textual mode like "Cash on Delivery"

    # --- shipping / address fields ---
    recipient_name = fields.StringField(max_length=200)
    phone = fields.StringField(max_length=50)
    address_line1 = fields.StringField()
    address_line2 = fields.StringField()
    city = fields.StringField()
    state = fields.StringField()
    pincode = fields.StringField()
    country = fields.StringField()
    delivery_instructions = fields.StringField()

    created_at = fields.DateTimeField(default=datetime.datetime.utcnow)
    meta = {'collection': 'flowfinds_orders', 'indexes': ['user_id', 'created_at']}


# ---------------------------------------------------------------------
# Django ORM mirror model for admin visibility (migratable)
# ---------------------------------------------------------------------
class OrderRecord(djmodels.Model):
    """
    Mirror of an Order for display in Django admin.
    Stores a reference to the Mongo order id, user FK (optional),
    totals, address fields, items as JSON string, created_at.
    """
    mongo_order_id = djmodels.CharField(max_length=64, unique=True, help_text="MongoEngine Order ID")
    user = djmodels.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=djmodels.SET_NULL)
    total = djmodels.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = djmodels.CharField(max_length=30, default='pending')
    payment_id = djmodels.CharField(max_length=200, blank=True)

    # shipping fields
    recipient_name = djmodels.CharField(max_length=200, blank=True)
    phone = djmodels.CharField(max_length=50, blank=True)
    address_line1 = djmodels.CharField(max_length=255, blank=True)
    address_line2 = djmodels.CharField(max_length=255, blank=True)
    city = djmodels.CharField(max_length=120, blank=True)
    state = djmodels.CharField(max_length=120, blank=True)
    pincode = djmodels.CharField(max_length=30, blank=True)
    country = djmodels.CharField(max_length=120, blank=True)
    delivery_instructions = djmodels.TextField(blank=True)

    # items stored as JSON string: list of {product_id, title, price, quantity, image_url}
    items_json = djmodels.TextField(blank=True)

    created_at = djmodels.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "FlowFinds Order (record)"
        verbose_name_plural = "FlowFinds Orders (records)"

    def __str__(self):
        return f"Order {self.mongo_order_id} — ₹{self.total}"

    def items(self):
        try:
            return json.loads(self.items_json or "[]")
        except Exception:
            return []


