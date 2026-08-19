export function calcInstallment(price, installments = 12) {
  const value = Number(price) / installments;
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function calcDiscount(price, compareAt) {
  if (!compareAt || compareAt <= price) return null;
  return Math.round(((compareAt - price) / compareAt) * 100);
}

function brand(name, slug, abbr, color, logoSlug = slug) {
  return {
    name,
    slug,
    abbr,
    color,
    query: name,
    logo: `/brands/${logoSlug}.png`,
  };
}

/** Marcas do mercado brasileiro com logo oficial (arquivo em /public/brands). */
export const CAR_BRANDS = [
  brand('Volkswagen', 'volkswagen', 'VW', '#001E50'),
  brand('Fiat', 'fiat', 'FI', '#9D2235'),
  brand('Chevrolet', 'chevrolet', 'GM', '#FFC72C'),
  brand('Hyundai', 'hyundai', 'HY', '#002C5F'),
  brand('Toyota', 'toyota', 'TY', '#EB0A1E'),
  brand('Honda', 'honda', 'HN', '#CC0000'),
  brand('Jeep', 'jeep', 'JP', '#1B3D2F'),
  brand('Renault', 'renault', 'RN', '#FFCC33'),
  brand('Nissan', 'nissan', 'NS', '#C3002F'),
  brand('Ford', 'ford', 'FD', '#003478'),
  brand('Peugeot', 'peugeot', 'PG', '#1B4073'),
  brand('Citroën', 'citroen', 'CT', '#DA291C'),
  brand('Mitsubishi', 'mitsubishi', 'MT', '#E60012'),
  brand('Kia', 'kia', 'KI', '#05141F'),
  brand('BMW', 'bmw', 'BM', '#0066B1'),
  brand('Mercedes-Benz', 'mercedes-benz', 'MB', '#1A1A1A'),
  brand('Audi', 'audi', 'AU', '#BB0A30'),
  brand('Volvo', 'volvo', 'VL', '#003057'),
  brand('Land Rover', 'land-rover', 'LR', '#005A2B'),
  brand('Porsche', 'porsche', 'PO', '#D5001C'),
  brand('BYD', 'byd', 'BY', '#FF6B00'),
  brand('GWM', 'gwm', 'GW', '#00A651', 'great-wall'),
  brand('Haval', 'haval', 'HV', '#C8102E'),
  brand('Chery', 'chery', 'CH', '#B11A29'),
  brand('Omoda', 'omoda', 'OM', '#E10600'),
  brand('Jetour', 'jetour', 'JT', '#1B4B8A'),
  brand('RAM', 'ram', 'RM', '#C41E3A'),
  brand('Dodge', 'dodge', 'DG', '#C8102E'),
  brand('Suzuki', 'suzuki', 'SZ', '#E30613'),
  brand('Subaru', 'subaru', 'SB', '#013C7A'),
  brand('JAC', 'jac', 'JC', '#E31E24'),
  brand('Mini', 'mini', 'MN', '#000000'),
  brand('Mazda', 'mazda', 'MZ', '#101010'),
  brand('Troller', 'troller', 'TR', '#FF6600'),
  brand('Iveco', 'iveco', 'IV', '#1D4F91'),
  brand('Lexus', 'lexus', 'LX', '#1A1A1A'),
  brand('Jaguar', 'jaguar', 'JG', '#1A1A1A'),
  brand('Alfa Romeo', 'alfa-romeo', 'AR', '#A6192E'),
  brand('Tesla', 'tesla', 'TS', '#CC0000'),
  brand('DS', 'ds', 'DS', '#D4AF37'),
  brand('Cupra', 'cupra', 'CU', '#1A1A1A'),
  brand('Geely', 'geely', 'GL', '#1D5C46'),
  brand('Changan', 'changan', 'CA', '#C8102E'),
  brand('Zeekr', 'zeekr', 'ZK', '#111111'),
  brand('Lifan', 'lifan', 'LF', '#0055A5'),
  brand('Isuzu', 'isuzu', 'IS', '#ED1C24'),
  brand('Scania', 'scania', 'SC', '#1D4F91'),
  brand('SsangYong', 'ssangyong', 'SY', '#C8102E'),
];
