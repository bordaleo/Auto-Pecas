"""Importação CSV de peças para vendedores."""
from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation

from django.utils.text import slugify

from api.models import Product, Category

REQUIRED_COLUMNS = {'name', 'price', 'stock', 'image_url'}
OPTIONAL_COLUMNS = {
    'description', 'sku', 'oem_code', 'brand', 'compatible_vehicles',
    'part_condition', 'part_origin', 'warranty_days',
    'weight_kg', 'width_cm', 'height_cm', 'length_cm', 'category_slug',
}


def parse_csv_content(content: str) -> tuple[list[dict], list[str]]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return [], ['CSV vazio ou sem cabeçalho.']

    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        return [], [f'Colunas obrigatórias faltando: {", ".join(sorted(missing))}']

    rows = []
    errors = []
    for i, row in enumerate(reader, start=2):
        normalized = {k.strip().lower(): (v or '').strip() for k, v in row.items()}
        if not any(normalized.values()):
            continue
        for col in REQUIRED_COLUMNS:
            if not normalized.get(col):
                errors.append(f'Linha {i}: campo "{col}" obrigatório.')
                break
        else:
            rows.append(normalized)
    return rows, errors


def import_products_for_seller(seller, user, rows: list[dict]) -> tuple[int, list[str]]:
    created = 0
    errors = []

    for i, row in enumerate(rows, start=1):
        try:
            price = Decimal(row['price'].replace(',', '.'))
            stock = int(row['stock'])
            if price <= 0 or stock < 0:
                raise ValueError('preço/estoque inválido')
        except (InvalidOperation, ValueError):
            errors.append(f'Linha {i}: preço ou estoque inválido.')
            continue

        name = row['name'][:255]
        base_slug = slugify(name)[:200] or 'peca'
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        category = None
        cat_slug = row.get('category_slug', '')
        if cat_slug:
            category = Category.objects.filter(slug=cat_slug, is_active=True).first()

        warranty = 90
        if row.get('warranty_days'):
            try:
                warranty = int(row['warranty_days'])
            except ValueError:
                pass

        Product.objects.create(
            seller=seller,
            created_by=user,
            name=name,
            slug=slug,
            description=row.get('description', ''),
            sku=row.get('sku', '')[:80],
            oem_code=row.get('oem_code', '')[:80],
            brand=row.get('brand', '')[:120],
            compatible_vehicles=row.get('compatible_vehicles', ''),
            price=price,
            stock=stock,
            image_url=row['image_url'][:500],
            category=category,
            part_condition=row.get('part_condition') or 'new',
            part_origin=row.get('part_origin') or 'original',
            warranty_days=warranty,
            is_active=True,
        )
        created += 1

    return created, errors
