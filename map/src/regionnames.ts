let regionNames: Record<string, string> | null = null;

fetch("/assets/regionnames.json")
  .then((res) => res.json())
  .then((data) => {
    regionNames = data;
  })
  .catch(() => {
    console.warn("regionnames.json not found");
  });

export function getRegionName(region: number): string | null {
  if (!regionNames) return null;
  const key = region < 0 ? String(region + 65536) : String(region);
  return regionNames[key] ?? null;
}
