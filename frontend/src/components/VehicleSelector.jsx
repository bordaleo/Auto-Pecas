import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { ChevronLeft, Check, Search, X } from 'lucide-react';
import { api, productList } from '../api/client';
import {
  getBaseModelName,
  getVariantLabel,
  groupModelsByBase,
  suggestBaseFromHint,
} from '../utils/vehicleModels';

const STEPS = [
  { id: 'brand', label: 'Marca' },
  { id: 'model', label: 'Modelo' },
  { id: 'version', label: 'Versão' },
  { id: 'year', label: 'Ano' },
];

const YEAR_OPTIONS = [];
for (let y = 2027; y >= 1990; y -= 1) YEAR_OPTIONS.push(y);

async function fetchAllModels(brand) {
  const limit = 1000;
  let offset = 0;
  let all = [];
  let total = 0;

  while (offset < 5000) {
    const params = new URLSearchParams({ brand, limit: String(limit), offset: String(offset) });
    const data = await api(`/vehicles/models/?${params}`);
    const batch = productList(data);
    total = data.count ?? batch.length;
    all = all.concat(batch);
    if (!batch.length || all.length >= total) break;
    offset += limit;
  }
  return all;
}

function normalize(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '');
}

function StepSearch({
  id,
  value,
  onChange,
  placeholder,
  disabled,
  onClear,
  onKeyDown,
}) {
  return (
    <div className="vehicle-selector__search">
      <Search size={16} className="vehicle-selector__search-icon" aria-hidden="true" />
      <input
        id={id}
        type="search"
        autoComplete="off"
        className="vehicle-selector__search-input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      {value && (
        <button type="button" className="vehicle-selector__search-clear" onClick={onClear} aria-label="Limpar">
          <X size={14} />
        </button>
      )}
    </div>
  );
}

/**
 * Seletor em 4 passos com autocomplete: Marca → Modelo → Versão → Ano
 */
export default function VehicleSelector({
  brands = [],
  brand = '',
  modelSlug = '',
  year = '',
  onChange,
  disabled = false,
  hintModels = [],
  modelHint = '',
  yearHint = '',
}) {
  const searchId = useId();
  const rootRef = useRef(null);
  const [step, setStep] = useState('brand');
  const [basePick, setBasePick] = useState('');
  const [query, setQuery] = useState('');
  const [allModels, setAllModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selectedModel = useMemo(
    () => allModels.find((m) => m.slug === modelSlug)
      || hintModels.find((m) => m.slug === modelSlug)
      || null,
    [allModels, hintModels, modelSlug],
  );

  const modelSource = allModels.length ? allModels : hintModels;
  const groups = useMemo(() => groupModelsByBase(modelSource), [modelSource]);
  const activeGroup = groups.find((g) => g.base === basePick) || null;

  const brandName = brands.find((b) => b.slug === brand)?.name || '';

  useEffect(() => {
    if (!brand) {
      setAllModels([]);
      setStep('brand');
      setBasePick('');
      setQuery('');
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    fetchAllModels(brand)
      .then((list) => {
        if (!cancelled) {
          setAllModels(list.length ? list : hintModels);
          setStep((s) => (s === 'brand' ? 'model' : s));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAllModels(hintModels);
          setError(hintModels.length ? '' : 'Não foi possível carregar os modelos.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [brand]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (modelSlug && selectedModel) {
      setBasePick(getBaseModelName(selectedModel.name));
      setStep('year');
    } else if (brand && !loading) {
      setStep((s) => (s === 'brand' ? 'model' : s));
    }
  }, [modelSlug, selectedModel, brand, loading]);

  useEffect(() => {
    if (!brand || basePick || modelSlug) return;
    const source = allModels.length ? allModels : hintModels;
    if (!source.length || !modelHint) return;
    const suggested = suggestBaseFromHint(modelHint, source);
    if (suggested && groups.some((g) => g.base === suggested)) {
      setBasePick(suggested);
      setStep('version');
      setQuery('');
    }
  }, [brand, allModels, hintModels, modelHint, modelSlug, basePick, groups]);

  useEffect(() => {
    setQuery('');
  }, [step]);

  const emit = (patch) => onChange(patch);

  const pickBrand = (b) => {
    emit({ vehicle_brand: b.slug, vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
    setBasePick('');
    setQuery('');
    setStep('model');
  };

  const pickBase = (base) => {
    const group = groups.find((g) => g.base === base);
    if (!group) return;
    setBasePick(base);
    setQuery('');
    if (group.variants.length === 1) {
      const m = group.variants[0];
      emit({
        vehicle_model: m.slug,
        vehicle_year: '',
        vehicle_model_name: m.name,
      });
      setStep('year');
    } else {
      emit({ vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
      setStep('version');
    }
  };

  const pickVariant = (m) => {
    emit({
      vehicle_model: m.slug,
      vehicle_year: '',
      vehicle_model_name: m.name,
    });
    setQuery('');
    setStep('year');
  };

  const pickYear = (y) => {
    emit({ vehicle_year: y ? String(y) : '' });
  };

  const skipYear = () => {
    emit({ vehicle_year: '' });
  };

  const handleYearSelect = (event) => {
    const { value } = event.target;
    if (value === 'skip') {
      skipYear();
    } else {
      pickYear(value);
    }
  };

  const goBack = () => {
    setQuery('');
    if (step === 'year') {
      if (activeGroup && activeGroup.variants.length > 1) {
        emit({ vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
        setStep('version');
      } else {
        emit({ vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
        setBasePick('');
        setStep('model');
      }
    } else if (step === 'version') {
      setBasePick('');
      emit({ vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
      setStep('model');
    } else if (step === 'model') {
      emit({ vehicle_brand: '', vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
      setBasePick('');
      setStep('brand');
    }
  };

  const nq = normalize(query);

  const filteredBrands = useMemo(() => {
    if (!nq) return brands;
    return brands.filter(
      (b) => normalize(b.name).includes(nq) || normalize(b.slug).includes(nq.replace(/\s+/g, '-')),
    );
  }, [brands, nq]);

  const filteredGroups = useMemo(() => {
    if (!nq) return groups;
    return groups.filter(
      (g) => normalize(g.base).includes(nq)
        || g.variants.some((v) => normalize(v.name).includes(nq)),
    );
  }, [groups, nq]);

  const filteredVariants = useMemo(() => {
    if (!activeGroup) return [];
    if (!nq) return activeGroup.variants;
    return activeGroup.variants.filter(
      (m) => normalize(m.name).includes(nq)
        || normalize(getVariantLabel(activeGroup.base, m.name)).includes(nq),
    );
  }, [activeGroup, nq]);

  const stepOptions = useMemo(() => {
    if (step === 'brand') return filteredBrands.map((b) => ({ key: b.slug, pick: () => pickBrand(b) }));
    if (step === 'model') return filteredGroups.map((g) => ({ key: g.base, pick: () => pickBase(g.base) }));
    if (step === 'version') return filteredVariants.map((m) => ({ key: m.id, pick: () => pickVariant(m) }));
    return [];
  }, [step, filteredBrands, filteredGroups, filteredVariants]); // eslint-disable-line react-hooks/exhaustive-deps

  const [highlight, setHighlight] = useState(0);

  useEffect(() => {
    setHighlight(0);
  }, [step, query]);

  const handleSearchKeyDown = (event) => {
    if (!stepOptions.length) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlight((i) => Math.min(i + 1, stepOptions.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlight((i) => Math.max(i - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      stepOptions[highlight]?.pick();
    }
  };

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  const searchPlaceholder = {
    brand: 'Digite a marca: BYD, Volkswagen, Fiat...',
    model: `Digite o modelo${brandName ? ` ${brandName}` : ''}: Seal, Polo, Gol...`,
    version: `Digite a versão${basePick ? ` ${basePick}` : ''}: Elétrico, Classic...`,
  }[step] || '';

  return (
    <div className="vehicle-selector" ref={rootRef}>
      <nav className="vehicle-selector__progress" aria-label="Passos do veículo">
        {STEPS.map((s, i) => (
          <div
            key={s.id}
            className={`vehicle-selector__step${i === stepIndex ? ' is-current' : ''}${i < stepIndex ? ' is-done' : ''}`}
          >
            <span className="vehicle-selector__step-num">
              {i < stepIndex ? <Check size={12} /> : i + 1}
            </span>
            <span className="vehicle-selector__step-label">{s.label}</span>
          </div>
        ))}
      </nav>

      {(brandName || selectedModel || year) && (
        <div className="vehicle-selector__summary">
          {[brandName, selectedModel?.name, year].filter(Boolean).join(' · ')}
        </div>
      )}

      {step !== 'brand' && (
        <button type="button" className="vehicle-selector__back" onClick={goBack}>
          <ChevronLeft size={16} aria-hidden="true" />
          Voltar
        </button>
      )}

      {loading && <p className="vehicle-selector__hint">Carregando modelos...</p>}
      {error && <p className="vehicle-selector__error">{error}</p>}

      {!loading && step !== 'year' && (
        <StepSearch
          id={`${searchId}-${step}`}
          value={query}
          onChange={setQuery}
          placeholder={searchPlaceholder}
          disabled={disabled}
          onClear={() => setQuery('')}
          onKeyDown={handleSearchKeyDown}
        />
      )}

      {!loading && step === 'brand' && (
        <div className="vehicle-selector__panel">
          <ul className="vehicle-selector__autolist" role="listbox" aria-label="Marcas">
            {filteredBrands.length === 0 ? (
              <li className="vehicle-selector__empty">Nenhuma marca encontrada</li>
            ) : (
              filteredBrands.map((b, i) => (
                <li key={b.slug}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={highlight === i}
                    className={`vehicle-selector__autocomplete${brand === b.slug ? ' is-selected' : ''}${highlight === i ? ' is-highlighted' : ''}`}
                    onClick={() => pickBrand(b)}
                    disabled={disabled}
                  >
                    <span className="vehicle-selector__autocomplete-main">{b.name}</span>
                    {b.model_count != null && (
                      <span className="vehicle-selector__autocomplete-meta">{b.model_count} modelos</span>
                    )}
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}

      {!loading && step === 'model' && brand && (
        <div className="vehicle-selector__panel">
          <ul className="vehicle-selector__autolist" role="listbox" aria-label="Modelos">
            {filteredGroups.length === 0 ? (
              <li className="vehicle-selector__empty">Nenhum modelo encontrado</li>
            ) : (
              filteredGroups.map(({ base, variants }, i) => (
                <li key={base}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={highlight === i}
                    className={`vehicle-selector__autocomplete${basePick === base ? ' is-selected' : ''}${highlight === i ? ' is-highlighted' : ''}`}
                    onClick={() => pickBase(base)}
                    disabled={disabled}
                  >
                    <span className="vehicle-selector__autocomplete-main">{base}</span>
                    <span className="vehicle-selector__autocomplete-meta">
                      {variants.length > 1 ? `${variants.length} versões` : '1 versão'}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}

      {!loading && step === 'version' && activeGroup && (
        <div className="vehicle-selector__panel">
          <p className="vehicle-selector__panel-subtitle">Versões do {activeGroup.base}</p>
          <ul className="vehicle-selector__autolist" role="listbox" aria-label="Versões">
            {filteredVariants.length === 0 ? (
              <li className="vehicle-selector__empty">Nenhuma versão encontrada</li>
            ) : (
              filteredVariants.map((m, i) => {
                const label = getVariantLabel(activeGroup.base, m.name);
                const display = label === 'Padrão' ? activeGroup.base : `${activeGroup.base} ${label}`;
                return (
                  <li key={m.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={highlight === i}
                      className={`vehicle-selector__autocomplete${modelSlug === m.slug ? ' is-selected' : ''}${highlight === i ? ' is-highlighted' : ''}`}
                      onClick={() => pickVariant(m)}
                      disabled={disabled}
                    >
                      <span className="vehicle-selector__autocomplete-main">{display}</span>
                    </button>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}

      {!loading && step === 'year' && selectedModel && (
        <div className="vehicle-selector__panel">
          <label htmlFor={`${searchId}-year`} className="vehicle-selector__year-label">
            Ano do veículo <span className="vehicle-selector__year-optional">(opcional)</span>
          </label>
          <select
            id={`${searchId}-year`}
            className="vehicle-selector__year-select"
            value={year || ''}
            onChange={handleYearSelect}
            disabled={disabled}
          >
            <option value="">
              {yearHint ? `Sugerido: ${yearHint} — ou escolha abaixo` : 'Selecione o ano (opcional)'}
            </option>
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
            <option value="skip">Pular — mostrar peças de todos os anos</option>
          </select>
          <p className="vehicle-selector__hint">
            As peças já estão filtradas por {selectedModel.name}. Refine pelo ano se quiser.
          </p>
        </div>
      )}
    </div>
  );
}
