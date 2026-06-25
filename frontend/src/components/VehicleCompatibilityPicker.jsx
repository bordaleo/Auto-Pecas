import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { api, productList } from '../api/client';
import VehicleCompatAdder from './VehicleCompatAdder';
import {
  compatEntryKey,
  formatCompatLabel,
  normalizeCompatEntry,
} from '../utils/vehicleCompat';

export default function VehicleCompatibilityPicker({
  selectedEntries = [],
  onChange,
  required = false,
}) {
  const [brands, setBrands] = useState([]);
  const [brandsLoading, setBrandsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [yearPickModel, setYearPickModel] = useState(null);
  const [quickYears, setQuickYears] = useState(new Set());

  useEffect(() => {
    setBrandsLoading(true);
    api('/catalog/filters/')
      .then((data) => setBrands(data.vehicle_brands || []))
      .catch(() => api('/vehicles/brands/').then(setBrands))
      .catch(() => setBrands([]))
      .finally(() => setBrandsLoading(false));
  }, []);

  useEffect(() => {
    const q = search.trim();
    if (q.length < 2) {
      setSearchResults([]);
      return undefined;
    }

    let cancelled = false;
    setSearchLoading(true);
    const timer = setTimeout(() => {
      const params = new URLSearchParams({ q, limit: '40' });
      api(`/vehicles/search/?${params}`)
        .then((data) => {
          if (!cancelled) setSearchResults(productList(data));
        })
        .catch(() => {
          if (!cancelled) setSearchResults([]);
        })
        .finally(() => {
          if (!cancelled) setSearchLoading(false);
        });
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search]);

  const selectedKeys = useMemo(
    () => new Set(selectedEntries.map(compatEntryKey)),
    [selectedEntries],
  );

  const addBatch = (entries) => {
    const merged = [...selectedEntries];
    const keys = new Set(merged.map(compatEntryKey));
    entries.forEach((entry) => {
      const key = compatEntryKey(entry);
      if (!keys.has(key)) {
        merged.push(entry);
        keys.add(key);
      }
    });
    onChange(merged);
  };

  const removeEntry = (entry) => {
    const key = compatEntryKey(entry);
    onChange(selectedEntries.filter((e) => compatEntryKey(e) !== key));
  };

  const openQuickYearPick = (model) => {
    setYearPickModel(model);
    setQuickYears(new Set());
  };

  const confirmQuickYears = () => {
    if (!yearPickModel || quickYears.size === 0) return;
    const entries = [...quickYears]
      .sort((a, b) => a - b)
      .map((y) => normalizeCompatEntry(yearPickModel, y, y));
    addBatch(entries);
    setYearPickModel(null);
    setQuickYears(new Set());
  };

  const addQuickAllYears = (model) => {
    addBatch([normalizeCompatEntry(model, null, null)]);
    setYearPickModel(null);
  };

  const quickYearsList = useMemo(() => {
    if (!yearPickModel) return [];
    const ys = Math.max(yearPickModel.year_start || 1990, 1990);
    const ye = Math.min(yearPickModel.year_end || 2027, 2027);
    const list = [];
    for (let y = ye; y >= ys; y -= 1) list.push(y);
    return list;
  }, [yearPickModel]);

  return (
    <div className="vehicle-compat-picker">
      <div className="form-group">
        <label>
          Veículos compatíveis
          {required && ' *'}
        </label>
        <p className="field-hint">
          Escolha marca, modelo, versão e os anos em que a peça serve. Você pode adicionar vários de uma vez.
        </p>
      </div>

      {selectedEntries.length > 0 && (
        <div className="vehicle-selected-chips">
          <span className="vehicle-selected-count">
            {selectedEntries.length} compatibilidade{selectedEntries.length > 1 ? 's' : ''}
          </span>
          {selectedEntries.map((entry) => (
            <span key={compatEntryKey(entry)} className="vehicle-chip">
              {formatCompatLabel(entry)}
              <button type="button" aria-label="Remover" onClick={() => removeEntry(entry)}>×</button>
            </span>
          ))}
        </div>
      )}

      {!brandsLoading && (
        <VehicleCompatAdder
          brands={brands}
          selectedEntries={selectedEntries}
          onAddBatch={addBatch}
        />
      )}

      <div className="vehicle-compat-search">
        <label htmlFor="vehicle-compat-quick-search">Busca rápida</label>
        <div className="vehicle-compat-search__input-wrap">
          <Search size={16} aria-hidden="true" />
          <input
            id="vehicle-compat-quick-search"
            type="search"
            placeholder="Ex: Gol, Argo, Seal Elétrico..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {searchLoading && <p className="field-hint">Buscando...</p>}
        {!searchLoading && search.trim().length >= 2 && searchResults.length === 0 && (
          <p className="field-hint">Nenhum modelo encontrado.</p>
        )}
        {searchResults.length > 0 && !yearPickModel && (
          <ul className="vehicle-selector__autolist vehicle-compat-search__results">
            {searchResults.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  className="vehicle-selector__autocomplete"
                  onClick={() => openQuickYearPick(m)}
                >
                  <span className="vehicle-selector__autocomplete-main">
                    {m.brand_name} {m.name}
                  </span>
                  <span className="vehicle-selector__autocomplete-meta">Escolher anos</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {yearPickModel && (
          <div className="vehicle-compat-years vehicle-compat-years--inline">
            <p className="vehicle-selector__panel-subtitle">
              Anos — {yearPickModel.brand_name} {yearPickModel.name}
            </p>
            <div className="vehicle-compat-years__toolbar">
              <button type="button" className="btn-link" onClick={() => setQuickYears(new Set(quickYearsList))}>
                Marcar todos
              </button>
              <button type="button" className="btn-link" onClick={() => setQuickYears(new Set())}>Limpar</button>
              <button type="button" className="btn-link" onClick={() => setYearPickModel(null)}>Cancelar</button>
            </div>
            <div className="vehicle-compat-years__grid">
              {quickYearsList.map((y) => (
                <label key={y} className="vehicle-compat-years__item">
                  <input
                    type="checkbox"
                    checked={quickYears.has(y)}
                    onChange={() => {
                      setQuickYears((prev) => {
                        const next = new Set(prev);
                        if (next.has(y)) next.delete(y);
                        else next.add(y);
                        return next;
                      });
                    }}
                  />
                  <span>{y}</span>
                </label>
              ))}
            </div>
            <div className="vehicle-compat-years__actions">
              <button
                type="button"
                className="btn btn-accent"
                disabled={quickYears.size === 0}
                onClick={confirmQuickYears}
              >
                Adicionar {quickYears.size || ''} ano(s)
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => addQuickAllYears(yearPickModel)}>
                Todos os anos
              </button>
            </div>
          </div>
        )}
      </div>

      {required && selectedEntries.length === 0 && (
        <p className="field-hint field-hint-warn">Selecione ao menos um veículo compatível.</p>
      )}
    </div>
  );
}
