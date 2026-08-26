export interface TeleportPad {
  id: number;
  code: string;
  name: string;
  x: number;
  z: number;
}

const WORLD_MIN = 0;
const WORLD_MAX = 11520;

let padsPromise: Promise<TeleportPad[]> | null = null;

export function loadTeleportPads(): Promise<TeleportPad[]> {
  if (!padsPromise) {
    padsPromise = fetch("/assets/gamedata/teleports_full.json")
      .then((r) => r.json() as Promise<{ gates: GateRec[] }>)
      .then(({ gates }) => {
        const out: TeleportPad[] = [];
        for (const g of gates) {
          const wx = g.x + ((g.region % 256) - 76) * 1920;
          const wz = g.z + (Math.floor(g.region / 256) - 103) * 1920;
          if (wx < WORLD_MIN || wx > WORLD_MAX || wz < WORLD_MIN || wz > WORLD_MAX) continue;
          out.push({ id: g.id, code: g.code, name: g.name, x: wx, z: wz });
        }
        return out;
      });
  }
  return padsPromise;
}

interface GateRec {
  id: number;
  code: string;
  name: string;
  region: number;
  x: number;
  z: number;
}
