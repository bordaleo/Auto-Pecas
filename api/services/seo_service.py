"""Gera títulos e descrições SEO para produtos."""


def build_product_seo(product) -> dict:
    name = (product.name or 'Peça automotiva').strip()
    brand = (product.brand or '').strip()
    oem = (product.oem_code or '').strip()
    sku = (product.sku or '').strip()
    vehicles = (product.compatible_vehicles or '').strip()
    category = ''
    if product.category_id and getattr(product, 'category', None):
        category = product.category.name or ''

    title_parts = [name]
    if vehicles:
        title_parts.append(vehicles)
    elif category:
        title_parts.append(category)
    if oem:
        title_parts.append(f'OEM {oem}')
    elif sku:
        title_parts.append(sku)

    seo_title = ' '.join(title_parts)
    if brand and brand.lower() not in seo_title.lower():
        seo_title = f'{seo_title} {brand}'
    seo_title = f'{seo_title} | Galelugi Peças'[:70]

    desc_bits = [f'Compre {name}']
    if brand:
        desc_bits.append(f'marca {brand}')
    if vehicles:
        desc_bits.append(f'compatível com {vehicles}')
    if oem:
        desc_bits.append(f'código OEM {oem}')
    if sku:
        desc_bits.append(f'SKU {sku}')
    desc_bits.append('Frete para todo o Brasil. Pagamento seguro Mercado Pago.')
    seo_description = '. '.join(desc_bits)[:160]

    return {'seo_title': seo_title, 'seo_description': seo_description}
