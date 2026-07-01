/**
 * Compatibilidade veicular para cards do catálogo.
 * Retorna: 'fits' | 'verify' | null
 */
export function getVehicleCompatibility(product, vehicle) {
  const brand = vehicle?.vehicle_brand || '';
  const model = vehicle?.vehicle_model || '';
  const year = vehicle?.vehicle_year ? parseInt(vehicle.vehicle_year, 10) : null;

  const hasCompatData = Boolean(
    (product.vehicle_models && product.vehicle_models.length)
    || (product.compatible_vehicles && product.compatible_vehicles.trim()),
  );

  if (!brand && !model) {
    return hasCompatData ? 'verify' : null;
  }

  const models = product.vehicle_models || [];
  if (models.length) {
    const match = models.some((vm) => {
      if (brand && vm.brand_slug !== brand) return false;
      if (model && vm.slug !== model) return false;
      if (year) {
        const yStart = vm.year_start ?? 0;
        const yEnd = vm.year_end ?? 9999;
        if (year < yStart || year > yEnd) return false;
      }
      return true;
    });
    if (match) return 'fits';
  }

  const text = (product.compatible_vehicles || '').toLowerCase();
  if (text) {
    const brandName = brand.replace(/-/g, ' ');
    const modelName = model.replace(/-/g, ' ');
    const brandOk = !brand || text.includes(brand) || text.includes(brandName);
    const modelOk = !model || text.includes(model) || text.includes(modelName);
    const yearOk = !year || text.includes(String(year));
    if (brandOk && modelOk && yearOk) return 'fits';
  }

  return hasCompatData ? 'verify' : null;
}

export function compatibilityLabel(status) {
  if (status === 'fits') return 'Serve no seu veículo';
  if (status === 'verify') return 'Verificar compatibilidade';
  return null;
}
