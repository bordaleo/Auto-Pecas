import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Car, Search, X } from 'lucide-react';
import { api, productList } from '../api/client';
import {
  getBaseModelName,
  getVariantLabel,
  groupModelsByBase,
  suggestBaseFromHint,
  yearRangeForModel,
} from '../utils/vehicleModels';

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

function OlxSelect({
  id,
  label,
  placeholder,
  value,
  displayValue,
  options,
  onChange,
  disabled,
  searchable,
  required,
  hint,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [panelStyle, setPanelStyle] = useState(null);
  const [placement, setPlacement] = useState('bottom');
  const wrapRef = useRef(null);
  const triggerRef = useRef(null);
  const panelRef = useRef(null);

  const filtered = useMemo(() => {
    if (!searchable || !query.trim()) return options;
    const nq = normalize(query);
    return options.filter(
      (o) => normalize(o.label).includes(nq) || (o.meta && normalize(o.meta).includes(nq)),
    );
  }, [options, query, searchable]);

  const updatePanelPosition = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const maxPanel = 300;
    const gap = 6;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    const openUp = spaceBelow < 180 && spaceAbove > spaceBelow;
    const available = openUp ? spaceAbove : spaceBelow;
    const height = Math.min(maxPanel, Math.max(160, available));

    setPlacement(openUp ? 'top' : 'bottom');
    setPanelStyle({
      position: 'fixed',
      left: rect.left,
      width: rect.width,
      zIndex: 6000,
      maxHeight: height,
      ...(openUp
        ? { bottom: window.innerHeight - rect.top + gap }
        : { top: rect.bottom + gap }),
    });
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery('');
      setPanelStyle(null);
      return undefined;
    }
    updatePanelPosition();
    const onReflow = () => updatePanelPosition();
    window.addEventListener('resize', onReflow);
    window.addEventListener('scroll', onReflow, true);
    return () => {
      window.removeEventListener('resize', onReflow);
      window.removeEventListener('scroll', onReflow, true);
    };
  }, [open, updatePanelPosition]);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => {
      const inTrigger = wrapRef.current?.contains(e.target);
      const inPanel = panelRef.current?.contains(e.target);
      if (!inTrigger && !inPanel) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const selected = options.find((o) => o.value === value);

  const panel = open && panelStyle && createPortal(
    <div
      ref={panelRef}
      className={`vf-select__panel vf-select__panel--portal vf-select__panel--${placement}`}
      style={panelStyle}
      role="presentation"
    >
      {searchable && (
        <div className="vf-select__search">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            placeholder={`Buscar ${label.toLowerCase()}...`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
        </div>
      )}
      <ul className="vf-select__list" role="listbox" aria-label={label}>
        {filtered.length === 0 ? (
          <li className="vf-select__empty">Nenhum resultado</li>
        ) : (
          filtered.map((opt) => (
            <li key={opt.value}>
              <button
                type="button"
                role="option"
                aria-selected={value === opt.value}
                className={`vf-select__option${value === opt.value ? ' is-selected' : ''}`}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
              >
                <span className="vf-select__option-label">{opt.label}</span>
                {opt.meta && <small className="vf-select__option-meta">{opt.meta}</small>}
              </button>
            </li>
          ))
        )}
      </ul>
    </div>,
    document.body,
  );

  return (
    <div
      className={`vf-select${disabled ? ' is-disabled' : ''}${required ? ' is-required' : ''}${open ? ' is-open' : ''}`}
      ref={wrapRef}
    >
      <label htmlFor={id} className="vf-select__label">
        {label}
        {required && <span className="vf-select__req"> *</span>}
      </label>
      {hint && <p className="vf-select__hint">{hint}</p>}
      <button
        id={id}
        ref={triggerRef}
        type="button"
        className="vf-select__trigger"
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={selected || displayValue ? 'vf-select__value' : 'vf-select__placeholder'}>
          {displayValue || selected?.label || placeholder}
        </span>
        <ChevronDown size={18} className="vf-select__chevron" aria-hidden="true" />
      </button>
      {panel}
    </div>
  );
}

/**
 * Seletor em cascata estilo OLX: Marca → Modelo → Versão → Ano
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
  needsYear = false,
}) {
  const uid = useId();
  const [basePick, setBasePick] = useState('');
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
  const showVersion = Boolean(activeGroup && activeGroup.variants.length > 1);
  const modelYears = useMemo(() => yearRangeForModel(selectedModel), [selectedModel]);

  const brandName = brands.find((b) => b.slug === brand)?.name || '';

  useEffect(() => {
    if (!brand) {
      setAllModels([]);
      setBasePick('');
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    fetchAllModels(brand)
      .then((list) => {
        if (!cancelled) setAllModels(list.length ? list : hintModels);
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
    }
  }, [modelSlug, selectedModel]);

  useEffect(() => {
    if (!brand || basePick || modelSlug) return;
    const source = allModels.length ? allModels : hintModels;
    if (!source.length || !modelHint) return;
    const suggested = suggestBaseFromHint(modelHint, source);
    if (suggested && groups.some((g) => g.base === suggested)) {
      setBasePick(suggested);
    }
  }, [brand, allModels, hintModels, modelHint, modelSlug, basePick, groups]);

  const emit = (patch) => onChange(patch);

  const brandOptions = useMemo(
    () => brands.map((b) => ({
      value: b.slug,
      label: b.name,
      meta: b.model_count != null ? `${b.model_count} modelos` : undefined,
    })),
    [brands],
  );

  const modelOptions = useMemo(
    () => groups.map((g) => ({
      value: g.base,
      label: g.base,
      meta: g.variants.length > 1 ? `${g.variants.length} versões` : undefined,
    })),
    [groups],
  );

  const versionOptions = useMemo(() => {
    if (!activeGroup) return [];
    return activeGroup.variants.map((m) => {
      const label = getVariantLabel(activeGroup.base, m.name);
      const display = label === 'Padrão' ? activeGroup.base : `${activeGroup.base} ${label}`;
      return { value: m.slug, label: display };
    });
  }, [activeGroup]);

  const yearOptions = useMemo(() => {
    const years = modelYears.length
      ? modelYears
      : Array.from({ length: 38 }, (_, i) => 2027 - i);
    const opts = years.map((y) => ({ value: String(y), label: String(y) }));
    if (!needsYear) {
      opts.unshift({ value: '', label: 'Todos os anos' });
    }
    return opts;
  }, [modelYears, needsYear]);

  const handleBrand = (slug) => {
    emit({ vehicle_brand: slug, vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
    setBasePick('');
  };

  const handleModel = (base) => {
    const group = groups.find((g) => g.base === base);
    if (!group) return;
    setBasePick(base);
    if (group.variants.length === 1) {
      const m = group.variants[0];
      emit({
        vehicle_model: m.slug,
        vehicle_year: '',
        vehicle_model_name: m.name,
      });
    } else {
      emit({ vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
    }
  };

  const handleVersion = (slug) => {
    const m = activeGroup?.variants.find((v) => v.slug === slug);
    if (!m) return;
    emit({
      vehicle_model: slug,
      vehicle_year: '',
      vehicle_model_name: m.name,
    });
  };

  const handleYear = (y) => {
    emit({ vehicle_year: y || '' });
  };

  const clearAll = () => {
    emit({ vehicle_brand: '', vehicle_model: '', vehicle_year: '', vehicle_model_name: '' });
    setBasePick('');
  };

  const breadcrumb = [brandName, selectedModel?.name, year].filter(Boolean);

  return (
    <>
      {breadcrumb.length > 0 && (
        <div className="vf-breadcrumb">
          <Car size={15} className="vf-breadcrumb__icon" aria-hidden="true" />
          <span className="vf-breadcrumb__text">{breadcrumb.join(' · ')}</span>
          <button
            type="button"
            className="vf-breadcrumb__clear"
            onClick={clearAll}
            disabled={disabled}
            aria-label="Limpar veículo selecionado"
          >
            <X size={15} aria-hidden="true" />
          </button>
        </div>
      )}

      {loading && <p className="vf-status">Carregando modelos...</p>}
      {error && <p className="vf-status vf-status--error">{error}</p>}

      <OlxSelect
        id={`${uid}-brand`}
        label="Marca"
        placeholder="Selecione a marca"
        value={brand}
        options={brandOptions}
        onChange={handleBrand}
        disabled={disabled || loading}
        searchable
      />

      <OlxSelect
        id={`${uid}-model`}
        label="Modelo"
        placeholder={brand ? 'Selecione o modelo' : 'Escolha a marca primeiro'}
        value={basePick}
        options={modelOptions}
        onChange={handleModel}
        disabled={disabled || loading || !brand}
        searchable
      />

      {showVersion && (
        <OlxSelect
          id={`${uid}-version`}
          label="Versão"
          placeholder="Selecione a versão"
          value={modelSlug}
          options={versionOptions}
          onChange={handleVersion}
          disabled={disabled || !basePick}
          searchable
        />
      )}

      <OlxSelect
        id={`${uid}-year`}
        label="Ano"
        placeholder={needsYear ? 'Selecione o ano' : 'Todos os anos'}
        value={year}
        options={yearOptions}
        onChange={handleYear}
        disabled={disabled || !modelSlug}
        required={needsYear}
        hint={
          needsYear && !year
            ? 'Informe o ano do veículo para filtrar as peças corretas.'
            : undefined
        }
      />

      {!needsYear && year && (
        <button
          type="button"
          className="vf-skip-year"
          onClick={() => handleYear('')}
          disabled={disabled}
        >
          Mostrar todos os anos
        </button>
      )}
    </>
  );
}
