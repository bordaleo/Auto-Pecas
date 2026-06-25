import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft } from 'lucide-react';
import {
  formatModelYears,
  getBaseModelName,
  getVariantLabel,
  groupModelsByBase,
} from '../utils/vehicleModels';

/**
 * Seleção em 2 passos: modelo base → versão/motorização.
 */
export default function VehicleModelSteps({
  models = [],
  year = '',
  value = '',
  onChange,
  loading = false,
  compact = false,
  title = 'Modelo do veículo',
}) {
  const [step, setStep] = useState('base');
  const [basePick, setBasePick] = useState('');

  const groups = useMemo(() => groupModelsByBase(models, year), [models, year]);

  const selectedModel = useMemo(
    () => models.find((m) => m.slug === value) || null,
    [models, value],
  );

  const activeGroup = useMemo(
    () => groups.find((g) => g.base === basePick) || null,
    [groups, basePick],
  );

  useEffect(() => {
    if (!selectedModel) return;
    const base = getBaseModelName(selectedModel.name);
    setBasePick(base);
    const g = groups.find((x) => x.base === base);
    if (g && g.variants.length > 1) setStep('variant');
  }, [selectedModel, groups]);

  useEffect(() => {
    if (!value) {
      setStep('base');
      if (!selectedModel) setBasePick('');
    }
  }, [value, selectedModel]);

  const pickBase = (base) => {
    const group = groups.find((g) => g.base === base);
    if (!group) return;
    setBasePick(base);
    if (group.variants.length === 1) {
      onChange(group.variants[0].slug);
      setStep('base');
    } else {
      onChange('');
      setStep('variant');
    }
  };

  const backToBases = () => {
    setStep('base');
    setBasePick('');
    onChange('');
  };

  if (loading) {
    return (
      <div className="vehicle-steps vehicle-steps--loading">
        <p className="vehicle-steps__hint">Carregando modelos...</p>
      </div>
    );
  }

  if (!models.length) {
    return (
      <div className="vehicle-steps vehicle-steps--empty">
        <p className="vehicle-steps__hint">
          {year
            ? `Nenhum modelo para o ano ${year}. Tente outro ano ou marca.`
            : 'Nenhum modelo disponível para esta marca.'}
        </p>
      </div>
    );
  }

  return (
    <div className={`vehicle-steps${compact ? ' vehicle-steps--compact' : ''}`}>
      <div className="vehicle-steps__header">
        <span className="vehicle-steps__title">{title}</span>
        {year && <span className="vehicle-steps__year-badge">Ano {year}</span>}
      </div>

      {!year && (
        <p className="vehicle-steps__year-warn">
          Informe o <strong>ano do veículo</strong> — muitas peças só servem para anos específicos.
        </p>
      )}

      {step === 'base' && (
        <div className="vehicle-steps__section">
          <p className="vehicle-steps__step-label">1. Escolha o modelo</p>
          <div className="vehicle-steps__grid">
            {groups.map(({ base, variants }) => {
              const isActive = basePick === base;
              const isSelected = selectedModel && getBaseModelName(selectedModel.name) === base;
              return (
                <button
                  key={base}
                  type="button"
                  className={`vehicle-steps__base${isActive || isSelected ? ' is-active' : ''}`}
                  onClick={() => pickBase(base)}
                >
                  <span className="vehicle-steps__base-name">{base}</span>
                  {variants.length > 1 && (
                    <span className="vehicle-steps__base-meta">{variants.length} versões</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {step === 'variant' && activeGroup && (
        <div className="vehicle-steps__section">
          <button type="button" className="vehicle-steps__back" onClick={backToBases}>
            <ChevronLeft size={16} aria-hidden="true" />
            {activeGroup.base}
          </button>
          <p className="vehicle-steps__step-label">2. Escolha a versão</p>
          <ul className="vehicle-steps__variants">
            {activeGroup.variants.map((m) => {
              const label = getVariantLabel(activeGroup.base, m.name);
              const years = formatModelYears(m, year);
              const display = label === 'Padrão' ? activeGroup.base : `${activeGroup.base} ${label}`;
              return (
                <li key={m.id}>
                  <button
                    type="button"
                    className={`vehicle-steps__variant${value === m.slug ? ' is-selected' : ''}`}
                    onClick={() => onChange(m.slug)}
                  >
                    <span className="vehicle-steps__variant-name">{display}</span>
                    <span className="vehicle-steps__variant-years">{years}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {selectedModel && (
        <p className="vehicle-steps__selected">
          Selecionado: <strong>{selectedModel.name}</strong>
          {year ? ` · ${year}` : ''}
        </p>
      )}
    </div>
  );
}
