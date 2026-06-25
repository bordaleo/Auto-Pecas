/** Anos disponíveis para um modelo (decrescente). */
export function yearRangeForModel(model) {
  if (!model) return [];
  const ys = Math.max(model.year_start || 1990, 1980);
  const ye = Math.min(model.year_end || new Date().getFullYear(), new Date().getFullYear() + 1);
  const years = [];
  for (let y = ye; y >= ys; y -= 1) years.push(y);
  return years;
}

/** Agrupa modelos FIPE: Polo → [Polo, Polo Classic, Polo GTS...] */
export function getBaseModelName(name) {
  const trimmed = (name || '').trim();
  if (!trimmed) return '';
  return trimmed.split(/\s+/)[0];
}

export function modelCoversYear(model, year) {
  if (!year) return true;
  const y = parseInt(String(year), 10);
  if (Number.isNaN(y)) return true;
  return model.year_start <= y && model.year_end >= y;
}

export function groupModelsByBase(models) {
  const groups = new Map();
  for (const m of models) {
    const base = getBaseModelName(m.name);
    if (!groups.has(base)) groups.set(base, []);
    groups.get(base).push(m);
  }
  return [...groups.entries()]
    .map(([base, variants]) => ({
      base,
      variants: variants.sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => a.base.localeCompare(b.base));
}

/** Nome da versão sem o prefixo do modelo base. */
export function getVariantLabel(base, fullName) {
  const name = (fullName || '').trim();
  if (!base || name === base) return 'Padrão';
  if (name.toLowerCase().startsWith(base.toLowerCase())) {
    const rest = name.slice(base.length).trim().replace(/^[-./]\s*/, '');
    return rest || 'Padrão';
  }
  return name;
}

export function formatYearRange(model) {
  const ys = model.year_start;
  const ye = model.year_end;
  if (ys === ye) return String(ys);
  return `${ys}–${ye}`;
}

/** Sugere modelo base a partir do hint da placa ou lista de modelos. */
export function suggestBaseFromHint(modelHint, models = []) {
  const hint = (modelHint || '').trim();
  if (!hint) return '';
  const first = getBaseModelName(hint);
  const groups = groupModelsByBase(models);
  const exact = groups.find((g) => g.base.toLowerCase() === first.toLowerCase());
  if (exact) return exact.base;
  const partial = groups.find(
    (g) => g.base.toLowerCase().includes(first.toLowerCase())
      || first.toLowerCase().includes(g.base.toLowerCase()),
  );
  return partial?.base || first;
}
