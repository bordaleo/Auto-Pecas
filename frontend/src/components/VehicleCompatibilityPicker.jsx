import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = ['', ...Array.from({ length: CURRENT_YEAR - 1979 }, (_, i) => String(CURRENT_YEAR - i))];

function groupByBrand(models) {
  const groups = new Map();
  models.forEach((model) => {
    const key = model.brand_slug || model.brand_name;
    if (!groups.has(key)) {
      groups.set(key, {
        slug: model.brand_slug,
        name: model.brand_name,
        models: [],
      });
    }
    groups.get(key).models.push(model);
  });
  return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
}

export default function VehicleCompatibilityPicker({
  selectedIds = [],
  onChange,
  required = false,
}) {
  const [allModels, setAllModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [yearFilter, setYearFilter] = useState('');
  const [search, setSearch] = useState('');
  const [expandedBrands, setExpandedBrands] = useState({});

  useEffect(() => {
    setLoading(true);
    api('/vehicles/models/')
      .then((data) => {
        setAllModels(data);
        const initial = {};
        groupByBrand(data).forEach((brand) => {
          initial[brand.slug] = true;
        });
        setExpandedBrands(initial);
      })
      .catch(() => setAllModels([]))
      .finally(() => setLoading(false));
  }, []);

  const filteredGroups = useMemo(() => {
    const query = search.trim().toLowerCase();
    const year = yearFilter ? parseInt(yearFilter, 10) : null;

    const filtered = allModels.filter((model) => {
      if (year && (model.year_start > year || model.year_end < year)) return false;
      if (!query) return true;
      const label = `${model.brand_name} ${model.name}`.toLowerCase();
      return label.includes(query);
    });

    return groupByBrand(filtered);
  }, [allModels, yearFilter, search]);

  const selectedDetails = useMemo(
    () => allModels.filter((model) => selectedIds.includes(model.id)),
    [allModels, selectedIds],
  );

  const toggleModel = (id) => {
    onChange(
      selectedIds.includes(id)
        ? selectedIds.filter((item) => item !== id)
        : [...selectedIds, id],
    );
  };

  const removeSelected = (id) => {
    onChange(selectedIds.filter((item) => item !== id));
  };

  const toggleBrand = (slug) => {
    setExpandedBrands((prev) => ({ ...prev, [slug]: !prev[slug] }));
  };

  const selectAllInBrand = (brandModels) => {
    const ids = brandModels.map((m) => m.id);
    const merged = new Set([...selectedIds, ...ids]);
    onChange(Array.from(merged));
  };

  const clearBrand = (brandModels) => {
    const ids = new Set(brandModels.map((m) => m.id));
    onChange(selectedIds.filter((id) => !ids.has(id)));
  };

  return (
    <div className="vehicle-compat-picker">
      <div className="form-group">
        <label>
          Veículos compatíveis
          {required && ' *'}
        </label>
        <p className="field-hint">
          Marque todos os modelos que servem nesta peça. Você pode escolher vários de marcas diferentes.
        </p>
      </div>

      {selectedDetails.length > 0 && (
        <div className="vehicle-selected-chips">
          {selectedDetails.map((m) => (
            <span key={m.id} className="vehicle-chip">
              {m.brand_name} {m.name} ({m.year_start}-{m.year_end})
              <button type="button" aria-label="Remover" onClick={() => removeSelected(m.id)}>×</button>
            </span>
          ))}
        </div>
      )}

      <div className="vehicle-compat-toolbar">
        <div className="form-group">
          <label htmlFor="vehicle-search">Buscar modelo</label>
          <input
            id="vehicle-search"
            type="search"
            placeholder="Ex: Gol, Argo, Onix..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="vehicle-year-filter">Filtrar por ano</label>
          <select
            id="vehicle-year-filter"
            value={yearFilter}
            onChange={(e) => setYearFilter(e.target.value)}
          >
            <option value="">Todos os anos</option>
            {YEAR_OPTIONS.filter(Boolean).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && <p className="field-hint">Carregando modelos...</p>}

      {!loading && filteredGroups.length === 0 && (
        <p className="field-hint">Nenhum modelo encontrado. Tente outro termo ou remova o filtro de ano.</p>
      )}

      <div className="vehicle-brand-list">
        {filteredGroups.map((brand) => {
          const brandSelected = brand.models.filter((m) => selectedIds.includes(m.id)).length;
          const expanded = expandedBrands[brand.slug] !== false;

          return (
            <div key={brand.slug} className="vehicle-brand-section">
              <button
                type="button"
                className="vehicle-brand-header"
                onClick={() => toggleBrand(brand.slug)}
              >
                <span>
                  {brand.name}
                  {brandSelected > 0 && (
                    <span className="vehicle-brand-count">{brandSelected} selecionado{brandSelected > 1 ? 's' : ''}</span>
                  )}
                </span>
                <span className="vehicle-brand-toggle">{expanded ? '−' : '+'}</span>
              </button>

              {expanded && (
                <>
                  <div className="vehicle-brand-actions">
                    <button type="button" className="btn-link" onClick={() => selectAllInBrand(brand.models)}>
                      Marcar todos
                    </button>
                    {brandSelected > 0 && (
                      <button type="button" className="btn-link" onClick={() => clearBrand(brand.models)}>
                        Limpar marca
                      </button>
                    )}
                  </div>
                  <div className="vehicle-model-checks vehicle-model-grid">
                    {brand.models.map((m) => (
                      <label key={m.id} className="vehicle-model-option">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(m.id)}
                          onChange={() => toggleModel(m.id)}
                        />
                        <span>{m.name} <small>({m.year_start}-{m.year_end})</small></span>
                      </label>
                    ))}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>

      {required && selectedIds.length === 0 && (
        <p className="field-hint field-hint-warn">Selecione ao menos um veículo compatível.</p>
      )}
    </div>
  );
}
