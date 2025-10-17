from django.core.management.base import BaseCommand
import json
from flowfinds.models import Order, OrderRecord  # Order = MongoEngine Document; OrderRecord = Django model
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Backfill OrderRecord rows from MongoEngine Order documents (creates records only when missing)."

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        failed = 0
        User = get_user_model()

        for mo in Order.objects:
            mongo_id = str(mo.pk)
            if OrderRecord.objects.filter(mongo_order_id=mongo_id).exists():
                skipped += 1
                continue

            # build items list from embedded order items
            items_for_record = []
            try:
                for it in getattr(mo, 'items', []) or []:
                    items_for_record.append({
                        "product_id": getattr(it, 'product_id', '') or '',
                        "title": getattr(it, 'title', '') or '',
                        "price": str(getattr(it, 'price', '') or ''),
                        "quantity": int(getattr(it, 'quantity', 1) or 1),
                        "image_url": getattr(it, 'image_url', '') or ''
                    })
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Warning building items for {mongo_id}: {e}"))
                items_for_record = []

            try:
                user_obj = None
                try:
                    uid = getattr(mo, 'user_id', None)
                    if uid:
                        user_obj = User.objects.filter(pk=uid).first()
                except Exception:
                    user_obj = None

                OrderRecord.objects.create(
                    mongo_order_id=mongo_id,
                    user=user_obj,
                    total=getattr(mo, 'total', 0) or 0,
                    status=getattr(mo, 'status', '') or '',
                    payment_id=getattr(mo, 'payment_id', '') or '',
                    recipient_name=getattr(mo, 'recipient_name','') or '',
                    phone=getattr(mo, 'phone','') or '',
                    address_line1=getattr(mo,'address_line1','') or '',
                    address_line2=getattr(mo,'address_line2','') or '',
                    city=getattr(mo,'city','') or '',
                    state=getattr(mo,'state','') or '',
                    pincode=getattr(mo,'pincode','') or '',
                    country=getattr(mo,'country','') or '',
                    delivery_instructions=getattr(mo,'delivery_instructions','') or '',
                    items_json=json.dumps(items_for_record)
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created OrderRecord for {mongo_id}"))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"Failed to create OrderRecord for {mongo_id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Created: {created}, Skipped: {skipped}, Failed: {failed}"))
