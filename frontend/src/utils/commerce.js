export function calcInstallment(price, installments = 12) {
  const value = Number(price) / installments;
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function calcDiscount(price, compareAt) {
  if (!compareAt || compareAt <= price) return null;
  return Math.round(((compareAt - price) / compareAt) * 100);
}

export const CAR_BRANDS = [
  { name: 'Volkswagen', abbr: 'VW', query: 'VW', color: '#001E50' },
  { name: 'Chevrolet', abbr: 'GM', query: 'Chevrolet', color: '#FFC72C' },
  { name: 'Fiat', abbr: 'FI', query: 'Fiat', color: '#9D2235' },
  { name: 'Ford', abbr: 'FD', query: 'Ford', color: '#003478' },
  { name: 'Toyota', abbr: 'TY', query: 'Toyota', color: '#EB0A1E' },
  { name: 'Honda', abbr: 'HN', query: 'Honda', color: '#CC0000' },
  { name: 'Hyundai', abbr: 'HY', query: 'Hyundai', color: '#002C5F' },
  { name: 'Renault', abbr: 'RN', query: 'Renault', color: '#FFCC33' },
  { name: 'Nissan', abbr: 'NS', query: 'Nissan', color: '#C3002F' },
  { name: 'Jeep', abbr: 'JP', query: 'Jeep', color: '#1B3D2F' },
  { name: 'BMW', abbr: 'BM', query: 'BMW', color: '#0066B1' },
  { name: 'Mercedes', abbr: 'MB', query: 'Mercedes', color: '#1A1A1A' },
];
