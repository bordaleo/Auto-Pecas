import { useEffect, useId, useMemo, useState } from 'react';
import { Check, ChevronLeft, Plus, Search, X } from 'lucide-react';
import { api, productList } from '../api/client';
import { compatEntryKey, normalizeCompatEntry } from '../utils/vehicleCompat';
import {
  getBaseModelName,
  getVariantLabel,
  groupModelsByBase,
  yearRangeForModel,
} from '../utils/vehicleModels';

const STEPS = [
  { id: 'brand', label: 'Marca' },
  { id: 'model', label: 'Modelo' },
  { id: 'version', label: 'Versão' },
  { id: 'year', label: 'Ano' },
];

async function fetchBrandModels(brand) {
  const limit = 1000;
  let offset = 0;
  let all = [];

  while (offset < 5000) {
    const params = new URLSearchParams({ brand, limit: String(limit), offset: String(offset) });
    const data = await api(`/vehicles/models/?${params}`);
    const batch = productList(data);
    all = all.concat(batch);
    if (!batch.length || all.length >= (data.count ?? batch.length)) break;
    offset += limit;
  }
  return all;
}

function normalize(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '');
}

function StepSearch({ id, value, onChange, placeholder, disabled, onClear, onKeyDown }) {
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

/** Wizard: Marca → Modelo → Versão → Anos (multi-select) → adiciona à lista. */
export default function VehicleCompatAdder({
  brands = [],
  selectedEntries = [],
  onAddBatch,
  disabled = false,
}) {
  const searchId = useId();
  const [step, setStep] = useState('brand');
  const [brandSlug, setBrandSlug] = useState('');
  const [basePick, setBasePick] = useState('');
  const [pendingModel, setPendingModel] = useState(null);
  const [query, setQuery] = useState('');
  const [allModels, setAllModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [addedFlash, setAddedFlash] = useState('');
  const [selectedYears, setSelectedYears] = useState(new Set());

  const selectedKeys = useMemo(
    () => new Set(selectedEntries.map(compatEntryKey)),
    [selectedEntries],
  );

  const brandName = brands.find((b) => b.slug === brandSlug)?.name || '';
  const groups = useMemo(() => groupModelsByBase(allModels), [allModels]);
  const activeGroup = groups.find((g) => g.base === basePick) || null;
  const years = useMemo(() => yearRangeForModel(pendingModel), [pendingModel]);

  useEffect(() => {
    if (!brandSlug) {
      setAllModels([]);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    fetchBrandModels(brandSlug)
      .then((list) => {
        if (!cancelled) {
          setAllModels(list);
          setStep((s) => (s === 'brand' ? 'model' : s));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAllModels([]);
          setError('Não foi possível carregar os modelos desta marca.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [brandSlug]);

  useEffect(() => {
    setQuery('');
    if (step !== 'year') setSelectedYears(new Set());
  }, [step]);

  const resetWizard = () => {
    setBrandSlug('');
    setBasePick('');
    setPendingModel(null);
    setQuery('');
    setStep('brand');
    setAllModels([]);
    setSelectedYears(new Set());
    setError('');
  };

  const flash = (msg) => {
    setAddedFlash(msg);
    setTimeout(() => setAddedFlash(''), 2800);
  };

  const pickBrand = (b) => {
    setBrandSlug(b.slug);
    setBasePick('');
    setPendingModel(null);
    setQuery('');
    setStep('model');
  };

  const pickBase = (base) => {
    const group = groups.find((g) => g.base === base);
    if (!group) return;
    setBasePick(base);
    setQuery('');
    if (group.variants.length === 1) {
      goToYearStep(group.variants[0]);
    } else {
      setStep('version');
    }
  };

  const goToYearStep = (model) => {
    setPendingModel(model);
    setSelectedYears(new Set());
    setQuery('');
    setStep('year');
  };

  const pickVariant = (m) => {
    goToYearStep(m);
  };

  const toggleYear = (y) => {
    setSelectedYears((prev) => {
      const next = new Set(prev);
      if (next.has(y)) next.delete(y);
      else next.add(y);
      return next;
    });
  };

  const selectAllYears = () => {
    setSelectedYears(new Set(years));
  };

  const clearYears = () => {
    setSelectedYears(new Set());
  };

  const addSelectedYears = () => {
    if (!pendingModel || selectedYears.size === 0) return;
    const toAdd = [...selectedYears]
      .sort((a, b) => a - b)
      .map((y) => normalizeCompatEntry(pendingModel, y, y))
      .filter((e) => !selectedKeys.has(compatEntryKey(e)));
    if (!toAdd.length) {
      flash('Anos selecionados já estão na lista.');
      return;
    }
    onAddBatch(toAdd);
    flash(`${toAdd.length} ano(s) adicionado(s) para ${pendingModel.brand_name} ${pendingModel.name}.`);
    resetWizard();
  };

  const addAllModelYears = () => {
    if (!pendingModel) return;
    const entry = normalizeCompatEntry(pendingModel, null, null);
    if (selectedKeys.has(compatEntryKey(entry))) {
      flash('Este veículo (todos os anos) já está na lista.');
      return;
    }
    onAddBatch([entry]);
    flash(`${pendingModel.brand_name} ${pendingModel.name} — todos os anos.`);
    resetWizard();
  };

  const goBack = () => {
    setQuery('');
    if (step === 'year') {
      setPendingModel(null);
      setSelectedYears(new Set());
      if (activeGroup && activeGroup.variants.length > 1) {
        setStep('version');
      } else {
        setBasePick('');
        setStep('model');
      }
    } else if (step === 'version') {
      setBasePick('');
      setStep('model');
    } else if (step === 'model') {
      setBrandSlug('');
      setAllModels([]);
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
    if (step === 'brand') return filteredBrands.map((b) => ({ pick: () => pickBrand(b) }));
    if (step === 'model') return filteredGroups.map((g) => ({ pick: () => pickBase(g.base) }));
    if (step === 'version') return filteredVariants.map((m) => ({ pick: () => pickVariant(m) }));
    return [];
  }, [step, filteredBrands, filteredGroups, filteredVariants]); // eslint-disable-line react-hooks/exhaustive-deps

  const [highlight, setHighlight] = useState(0);

  useEffect(() => {
    setHighlight(0);
  }, [step, query]);

  const handleSearchKeyDown = (event) => {
    if (step === 'year') return;
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
  const pendingLabel = pendingModel
    ? `${pendingModel.brand_name} ${pendingModel.name}`
    : '';

  const searchPlaceholder = {
    brand: 'Digite a marca: BYD, Volkswagen, Fiat...',
    model: `Digite o modelo${brandName ? ` ${brandName}` : ''}: Seal, Polo, Gol...`,
    version: `Digite a versão${basePick ? ` ${basePick}` : ''}: Elétrico, Classic...`,
  }[step] || '';

  return (
    <div className="vehicle-compat-adder">
      <div className="vehicle-compat-adder__head">
        <Plus size={16} aria-hidden="true" />
        <span>Adicionar veículos compatíveis</span>
      </div>

      {addedFlash && <p className="vehicle-compat-adder__flash">{addedFlash}</p>}

      <nav className="vehicle-selector__progress vehicle-selector__progress--compact" aria-label="Passos">
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
                  className={`vehicle-selector__autocomplete${highlight === i ? ' is-highlighted' : ''}`}
                  onClick={() => pickBrand(b)}
                  disabled={disabled}
                >
                  <span className="vehicle-selector__autocomplete-main">{b.name}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}

      {!loading && step === 'model' && brandSlug && (
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
                  className={`vehicle-selector__autocomplete${highlight === i ? ' is-highlighted' : ''}`}
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
      )}

      {!loading && step === 'version' && activeGroup && (
        <>
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
                      className={`vehicle-selector__autocomplete${highlight === i ? ' is-highlighted' : ''}`}
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
        </>
      )}

      {!loading && step === 'year' && pendingModel && (
        <div className="vehicle-compat-years">
          <p className="vehicle-selector__panel-subtitle">
            Anos compatíveis — {pendingLabel}
          </p>
          <p className="vehicle-selector__hint">
            Marque um ou mais anos. Peças específicas costumam servir só em alguns anos.
          </p>
          <div className="vehicle-compat-years__toolbar">
            <button type="button" className="btn-link" onClick={selectAllYears}>Marcar todos</button>
            <button type="button" className="btn-link" onClick={clearYears}>Limpar</button>
          </div>
          <div className="vehicle-compat-years__grid">
            {years.map((y) => (
              <label key={y} className="vehicle-compat-years__item">
                <input
                  type="checkbox"
                  checked={selectedYears.has(y)}
                  onChange={() => toggleYear(y)}
                />
                <span>{y}</span>
              </label>
            ))}
          </div>
          <div className="vehicle-compat-years__actions">
            <button
              type="button"
              className="btn btn-accent btn-full"
              disabled={selectedYears.size === 0}
              onClick={addSelectedYears}
            >
              Adicionar {selectedYears.size > 0 ? `${selectedYears.size} ano(s)` : 'anos selecionados'}
            </button>
            <button type="button" className="btn btn-secondary btn-full" onClick={addAllModelYears}>
              Todos os anos do modelo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
