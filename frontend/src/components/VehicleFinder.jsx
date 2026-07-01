import { useState } from 'react';
import { api } from '../api/client';
import VehicleSelector from './VehicleSelector';

const MODES = [
  { id: 'plate', label: 'Placa' },
  { id: 'vin', label: 'VIN' },
];

const MODE_COPY = {
  plate: { label: 'Placa Mercosul ou antiga', placeholder: 'Ex: ABC1D23' },
  vin: { label: 'VIN (17 caracteres)', placeholder: 'Ex: 9BWZZZ377VT004251' },
};

function normalize(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '');
}

function pickBestModel(models, modelHint) {
  if (!models?.length) return null;
  if (models.length === 1) return models[0];
  if (!modelHint) return models[0];
  const hint = normalize(modelHint);
  return models.find((m) => normalize(m.name).includes(hint))
    || models.find((m) => hint.includes(normalize(m.name.split(' ')[0])))
    || models[0];
}

function resolveBrandSlug(data, brands) {
  const fromModel = data.vehicle_models?.[0]?.brand_slug;
  if (fromModel) return fromModel;
  const hint = (data.brand_hint || '').trim();
  if (!hint) return '';
  return brands.find((b) => normalize(b.name) === normalize(hint))?.slug
    || brands.find((b) => normalize(b.name).includes(normalize(hint)))?.slug
    || '';
}

export default function VehicleFinder({
  brands = [],
  brand = '',
  modelSlug = '',
  year = '',
  onChange,
  onApply,
  onApplyFilters,
  onClearFilters,
  showClearFilters = false,
  disabled = false,
}) {
  const [mode, setMode] = useState('plate');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [hintModels, setHintModels] = useState([]);
  const [modelHint, setModelHint] = useState('');
  const [needsYear, setNeedsYear] = useState(false);

  const resetResult = () => {
    setResult(null);
    setHintModels([]);
    setModelHint('');
    setNeedsYear(false);
  };

  const switchMode = (next) => {
    setMode(next);
    resetResult();
  };

  const runLookup = async (event) => {
    event.preventDefault();
    if (!input.trim()) return;

    setLoading(true);
    resetResult();

    try {
      const body = { year: year || undefined };
      const trimmed = input.trim();
      if (mode === 'vin') body.vin = trimmed;
      else body.plate = trimmed.replace(/\s/g, '');

      const data = await api('/vehicles/lookup/', {
        method: 'POST',
        body: JSON.stringify(body),
      });

      setResult(data);
      const models = data.vehicle_models || [];
      setHintModels(models);
      setModelHint(data.model_hint || '');

      const brandSlug = resolveBrandSlug(data, brands);
      const bestModel = pickBestModel(models, data.model_hint);
      const hasYear = Boolean(data.year_hint);
      const yearRequired = Boolean(data.year_estimated && !hasYear);
      setNeedsYear(yearRequired);

      const patch = {
        q: '',
        vehicle_brand: brandSlug,
        vehicle_model: bestModel?.slug || '',
        vehicle_year: hasYear ? String(data.year_hint) : '',
        vehicle_model_name: bestModel?.name || '',
      };

      if (!models.length && (data.brand_hint || data.model_hint)) {
        patch.q = [data.brand_hint, data.model_hint].filter(Boolean).join(' ');
      }

      onChange(patch);

      if (!patch.q && patch.vehicle_brand && patch.vehicle_model) {
        onApply(patch);
        if (hasYear) setNeedsYear(false);
      }
    } catch (err) {
      setResult({ error: true, message: err.message || 'Não foi possível consultar.' });
    } finally {
      setLoading(false);
    }
  };

  const handleCascadeChange = (patch) => {
    onChange(patch);
  };

  const copy = MODE_COPY[mode];

  return (
    <>
      <div className="catalog-filters-box">
        <h3>Seu veículo</h3>
        <p className="catalog-filters-box__lead">
          Encontre peças compatíveis com seu carro, moto ou caminhão
        </p>

        <div className="filter-row">
          <span className="filter-row__label">Buscar por</span>
          <div className="vin-lookup-tabs" role="tablist" aria-label="Forma de busca">
            {MODES.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={mode === id}
                className={`vin-lookup-tab${mode === id ? ' active' : ''}`}
                onClick={() => switchMode(id)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={runLookup}>
          <div className="filter-row">
            <label htmlFor="vf-quick-input">{copy.label}</label>
            <input
              id="vf-quick-input"
              className="vin-lookup-input"
              placeholder={copy.placeholder}
              value={input}
              onChange={(e) => setInput(mode === 'plate' ? e.target.value.toUpperCase() : e.target.value)}
              disabled={disabled || loading}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <button
            type="submit"
            className="btn btn-accent btn-full"
            disabled={disabled || loading || !input.trim()}
          >
            {loading ? 'Consultando...' : 'Identificar veículo'}
          </button>
        </form>

        {result?.message && !result.error && (
          <p className="catalog-vehicle-feedback catalog-vehicle-feedback--ok" role="status">
            {result.message}
          </p>
        )}
        {result?.error && (
          <p className="catalog-vehicle-feedback catalog-vehicle-feedback--err" role="alert">
            {result.message}
          </p>
        )}
      </div>

      <div className="catalog-filters-box">
        <h3>Marca e modelo</h3>
        <form onSubmit={onApplyFilters}>
          <VehicleSelector
            brands={brands}
            brand={brand}
            modelSlug={modelSlug}
            year={year}
            onChange={handleCascadeChange}
            disabled={disabled || loading}
            hintModels={hintModels}
            modelHint={modelHint || result?.model_hint || ''}
            yearHint={result?.year_hint || ''}
            needsYear={needsYear}
          />
          <button type="submit" className="btn btn-primary btn-full">Aplicar filtros</button>
          {showClearFilters && (
            <button
              type="button"
              className="btn btn-secondary btn-full catalog-clear-btn"
              onClick={onClearFilters}
            >
              Limpar filtros
            </button>
          )}
        </form>
      </div>
    </>
  );
}
