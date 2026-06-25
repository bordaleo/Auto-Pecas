import { useEffect, useState } from 'react';
import { api, productList } from '../api/client';
import VehicleModelSteps from './VehicleModelSteps';

async function fetchAllModels(brand, year) {
  const limit = 1000;
  let offset = 0;
  let all = [];
  let total = 0;

  while (offset < 5000) {
    const params = new URLSearchParams({ brand, limit: String(limit), offset: String(offset) });
    if (year) params.set('year', year);
    const data = await api(`/vehicles/models/?${params}`);
    const batch = productList(data);
    total = data.count ?? batch.length;
    all = all.concat(batch);
    if (!batch.length || all.length >= total) break;
    offset += limit;
  }
  return all;
}

export default function VehicleModelPicker({
  brand,
  year = '',
  value = '',
  onChange,
  disabled = false,
}) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!brand) {
      setModels([]);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    fetchAllModels(brand, year)
      .then((list) => {
        if (!cancelled) setModels(list);
      })
      .catch(() => {
        if (!cancelled) {
          setModels([]);
          setError('Não foi possível carregar os modelos.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [brand, year]);

  if (!brand) {
    return (
      <div className="vehicle-picker vehicle-picker--disabled">
        <input disabled placeholder="Selecione a marca do veículo primeiro" />
      </div>
    );
  }

  return (
    <div className="vehicle-picker">
      <VehicleModelSteps
        models={models}
        year={year}
        value={value}
        onChange={onChange}
        loading={loading || disabled}
      />
      {error && <p className="form-hint vehicle-picker__error">{error}</p>}
    </div>
  );
}
