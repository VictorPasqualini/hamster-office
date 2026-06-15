// Matemática isométrica (2:1) e pathfinding A* — funções puras.

export const TILE_W = 64;
export const TILE_H = 32;

export interface Tile {
  x: number;
  y: number;
}

export function isoToScreen(x: number, y: number, originX: number, originY: number) {
  return {
    sx: originX + (x - y) * (TILE_W / 2),
    sy: originY + (x + y) * (TILE_H / 2),
  };
}

export function screenToIso(sx: number, sy: number, originX: number, originY: number): Tile {
  const ax = (sx - originX) / (TILE_W / 2);
  const ay = (sy - originY) / (TILE_H / 2);
  return { x: Math.round((ax + ay) / 2), y: Math.round((ay - ax) / 2) };
}

export const key = (x: number, y: number) => `${x},${y}`;

function inBounds(x: number, y: number, w: number, h: number) {
  return x >= 0 && y >= 0 && x < w && y < h;
}

/**
 * A* em grid 4-direções. `blocked` contém células intransponíveis ("x,y").
 * Retorna o caminho (sem incluir o início); [] se inalcançável.
 */
export function findPath(
  start: Tile,
  goal: Tile,
  width: number,
  height: number,
  blocked: Set<string>
): Tile[] {
  if (start.x === goal.x && start.y === goal.y) return [];
  if (!inBounds(goal.x, goal.y, width, height) || blocked.has(key(goal.x, goal.y))) return [];

  const h = (a: Tile, b: Tile) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
  const open: Tile[] = [start];
  const cameFrom = new Map<string, string>();
  const g = new Map<string, number>([[key(start.x, start.y), 0]]);
  const f = new Map<string, number>([[key(start.x, start.y), h(start, goal)]]);

  while (open.length) {
    // nó com menor f
    let bi = 0;
    for (let i = 1; i < open.length; i++) {
      if ((f.get(key(open[i].x, open[i].y)) ?? Infinity) < (f.get(key(open[bi].x, open[bi].y)) ?? Infinity))
        bi = i;
    }
    const cur = open.splice(bi, 1)[0];
    if (cur.x === goal.x && cur.y === goal.y) {
      const path: Tile[] = [];
      let ck = key(cur.x, cur.y);
      while (cameFrom.has(ck)) {
        const [px, py] = ck.split(",").map(Number);
        path.unshift({ x: px, y: py });
        ck = cameFrom.get(ck)!;
      }
      return path;
    }
    const neighbors = [
      { x: cur.x + 1, y: cur.y },
      { x: cur.x - 1, y: cur.y },
      { x: cur.x, y: cur.y + 1 },
      { x: cur.x, y: cur.y - 1 },
    ];
    for (const n of neighbors) {
      if (!inBounds(n.x, n.y, width, height) || blocked.has(key(n.x, n.y))) continue;
      const tentative = (g.get(key(cur.x, cur.y)) ?? Infinity) + 1;
      const nk = key(n.x, n.y);
      if (tentative < (g.get(nk) ?? Infinity)) {
        cameFrom.set(nk, key(cur.x, cur.y));
        g.set(nk, tentative);
        f.set(nk, tentative + h(n, goal));
        if (!open.some((o) => o.x === n.x && o.y === n.y)) open.push(n);
      }
    }
  }
  return [];
}
