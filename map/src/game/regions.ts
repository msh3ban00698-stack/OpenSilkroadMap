export interface RegionDef {
  id: number;
  key: string;
  name: string;
  sx: number;
  sy: number;
  span: number;
}

// Authentic world regions generated from the VSRO packages. Each region is a
// 6x6 sector window rendered as its own 3D world (map/public/assets/img/
// silkroad/game/<key>/). Windows come from scripts/extract_regions.py.
export const REGIONS: RegionDef[] = [
  { id: 1, key: "region1", name: "Constantinople", sx: 76, sy: 103, span: 6 },
  { id: 2, key: "region2", name: "Jangan", sx: 164, sy: 94, span: 6 },
  { id: 3, key: "region3", name: "Donwhang", sx: 150, sy: 99, span: 6 },
  { id: 4, key: "region4", name: "Hotan", sx: 132, sy: 89, span: 6 },
  { id: 5, key: "region5", name: "Samarkand", sx: 104, sy: 102, span: 6 },
  { id: 6, key: "region6", name: "Baghdad", sx: 86, sy: 84, span: 6 },
  { id: 7, key: "region7", name: "Alexandria", sx: 45, sy: 90, span: 6 },
  { id: 8, key: "region8", name: "Mt. Roc", sx: 106, sy: 89, span: 6 },
  { id: 9, key: "region9", name: "Jupiter Temple", sx: 199, sy: 88, span: 6 },
];

export const START_REGION = REGIONS[0];

export function regionById(id: number): RegionDef {
  return REGIONS.find((r) => r.id === id) ?? REGIONS[0];
}

// Map an SRO sector id (x = region & 0xff, y = region >> 8) to a RegionDef.
export function regionForSector(region: number): RegionDef | null {
  const rx = region & 0xff;
  const ry = region >> 8;
  return REGIONS.find((r) => rx >= r.sx && rx < r.sx + r.span && ry >= r.sy && ry < r.sy + r.span) ?? null;
}
