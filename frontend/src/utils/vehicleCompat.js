export function compatEntryKey(entry) {
  const ys = entry.year_start ?? 'all';
  const ye = entry.year_end ?? 'all';
  return `${entry.model_id}-${ys}-${ye}`;
}

export function formatCompatLabel(entry) {
  const brand = entry.brand_name || entry.brand || '';
  const name = entry.name || '';
  const ys = entry.compat_year_start ?? entry.year_start;
  const ye = entry.compat_year_end ?? entry.year_end;
  if (ys != null && ye != null) {
    const years = ys === ye ? String(ys) : `${ys}-${ye}`;
    return `${brand} ${name} (${years})`.trim();
  }
  return `${brand} ${name}`.trim();
}

export function vehicleModelsToCompat(models = []) {
  return models.map((v) => ({
    model_id: v.id,
    year_start: v.compat_year_start ?? null,
    year_end: v.compat_year_end ?? null,
    name: v.name,
    brand_name: v.brand || v.brand_name,
    brand_slug: v.brand_slug,
  }));
}

export function normalizeCompatEntry(model, yearStart = null, yearEnd = null) {
  const ys = yearStart;
  const ye = yearEnd ?? yearStart;
  return {
    model_id: model.id,
    year_start: ys,
    year_end: ye,
    name: model.name,
    brand_name: model.brand_name || model.brand,
    brand_slug: model.brand_slug,
  };
}
