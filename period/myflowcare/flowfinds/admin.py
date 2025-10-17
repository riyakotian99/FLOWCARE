# flowfinds/admin.py

from django.contrib import admin
from django.utils.safestring import mark_safe
import json
from .models import OrderRecord

@admin.register(OrderRecord)
class OrderRecordAdmin(admin.ModelAdmin):
    list_display = ('mongo_order_id', 'user', 'total', 'status', 'payment_id', 'created_at')
    list_filter = ('status', 'payment_id', 'created_at')
    search_fields = (
        'mongo_order_id',
        'user__username',
        'recipient_name',
        'phone',
        'address_line1',
        'pincode'
    )

    # show human-friendly items via display_items; keep raw JSON readonly but hidden by default
    readonly_fields = ('mongo_order_id', 'created_at', 'display_items', 'items_json')
    fieldsets = (
        (None, {
            'fields': ('mongo_order_id', 'user', 'total', 'status', 'payment_id', 'created_at')
        }),
        ('Shipping', {
            'fields': (
                'recipient_name',
                'phone',
                'address_line1',
                'address_line2',
                'city',
                'state',
                'pincode',
                'country',
                'delivery_instructions'
            )
        }),
        ('Items (readable)', {
            'fields': ('display_items',)
        }),
        ('Items (raw JSON)', {
            'classes': ('collapse',),
            'fields': ('items_json',)
        }),
    )

    def display_items(self, obj):
        """
        Convert items_json into HTML lines like:
        Comfort Pads (20 pack) × 2 — ₹199.00
        Also shows small thumbnail if image_url present.
        """
        try:
            items = json.loads(obj.items_json or "[]")
        except Exception:
            items = []

        if not items:
            return mark_safe("<em>No items recorded</em>")

        lines = []
        for it in items:
            title = it.get('title') or it.get('product_id') or 'Item'
            qty = it.get('quantity', 1)
            price = it.get('price', '')
            image_url = it.get('image_url') or ''

            # thumbnail HTML (small)
            thumb_html = ''
            if image_url:
                thumb_html = f'<img src="{image_url}" style="height:36px; width:auto; margin-right:8px; vertical-align:middle; border-radius:4px;">'

            if price:
                line = f'{thumb_html}{title} &times; {qty} — ₹{price}'
            else:
                line = f'{thumb_html}{title} &times; {qty}'

            lines.append(line)

        html = "<br>".join(lines)
        return mark_safe(html)

    display_items.short_description = "Items"
