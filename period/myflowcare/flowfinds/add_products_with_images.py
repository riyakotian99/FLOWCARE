# flowfinds/add_products_with_images.py
from decimal import Decimal
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from pathlib import Path
from django.utils.text import slugify
from flowfinds.models import Product
import sys

# use folder relative to this file

BASE_DIR = Path(sys.path[0]) / "flowfinds"
IMAGE_FOLDER = BASE_DIR / "sample_images"


products = [
    {"title":"Comfort Pads (20 pack)", "slug":"comfort-pads-20", "description":"Soft long-lasting sanitary pads — 20 pack", "price": Decimal('199.00'), "stock": 50, "image_filename": "comfort-pads-20.jpg"},
    {"title":"Ultra Thin Tampons (16 pcs)", "slug":"ultra-tampons-16", "description":"Leak-free, comfortable tampons (16 pcs)", "price": Decimal('149.00'), "stock": 80, "image_filename": "ultra-tampons-16.jpg"},
    {"title":"Silicone Menstrual Cup", "slug":"silicone-menstrual-cup", "description":"Reusable medical-grade silicone menstrual cup", "price": Decimal('499.00'), "stock": 30, "image_filename": "silicone-menstrual-cup.jpg"},
    {"title":"Period Underwear (1 pc)", "slug":"period-underwear", "description":"Absorbent period underwear — comfortable & reusable", "price": Decimal('699.00'), "stock": 40, "image_filename": "period-underwear.jpg"},
    {"title":"Reusable Menstrual Disc", "slug":"menstrual-disc", "description":"Flexible menstrual disc for leak-free protection", "price": Decimal('549.00'), "stock": 20, "image_filename": "menstrual-disc.jpg"},
    {"title":"Portable Heating Pad", "slug":"portable-heating-pad", "description":"Reusable heating pad for cramps — microwaveable", "price": Decimal('249.00'), "stock": 60, "image_filename": "portable-heating-pad.jpg"},
    {"title": "Pain Killer Tablets (Strip of 10)", "slug": "pain-killer", "description": "Fast relief painkiller tablets for period cramps (strip of 10)", "price": Decimal('99.00'), "stock": 100, "image_filename": "pain-killer.jpg"},
    {"title": "Feminine Wipes (30 pcs)", "slug": "cleansing-wipes", "description": "Wipes used to cleanse the outer area of the genitals, the vulva", "price": Decimal('100.00'), "stock": 40, "image_filename": "wipes.jpg"},
    {"title": "Hello Wash (100ml pack 1)", "slug": "vaginal-wash", "description": "Gentle soap used to wash the external vulva area", "price": Decimal('214.00'), "stock": 20, "image_filename": "soap.jpg"},
    {"title": "Sanitary Napkin Pouches (Pack of 5)", "slug": "sanitarypad-pouches", "description": "For keeping your sanitary pads", "price": Decimal('230.00'), "stock": 20, "image_filename": "poches.jpg"},
]

added = []
for item in products:
    # normalize slug
    slug = slugify(item.get("slug") or item["title"])
    # skip if slug already exists
    if Product.objects(slug=slug).first():
        print(f"Skipping existing: {slug}")
        continue

    image_url = ""
    img_path = IMAGE_FOLDER / item.get("image_filename", "")
    if img_path.exists():
        try:
            with open(img_path, "rb") as f:
                data = f.read()
            save_path = f"flowfinds/products/{img_path.name}"
            saved_name = default_storage.save(save_path, ContentFile(data))
            image_url = default_storage.url(saved_name)
            print(f"Saved image for {slug} -> {saved_name}")
        except Exception as e:
            print("Image save failed for", slug, ":", e)
            image_url = ""
    else:
        print("Image file not found for", slug, "expected at:", str(img_path))
        image_url = ""

    p = Product(
        title=item['title'],
        slug=slug,
        description=item['description'],
        price=item['price'],
        stock=item['stock'],
        image_url=image_url,
        active=True
    )
    p.save()
    added.append(p)
    print("Added product:", p.title)

print(f"Done. Added {len(added)} product(s).")
