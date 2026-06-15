"use client";

import { useEffect, useRef } from "react";
import type { Application, Container } from "pixi.js";
import { useOfficeSocket, type OfficeMe } from "@/lib/ws";
import { TILE_W, TILE_H, isoToScreen, screenToIso, key, findPath, type Tile } from "@/lib/iso";
import type { OfficeAvatar, Scene } from "@/lib/types";

const COLOR_HEX: Record<string, number> = {
  orange: 0xe8872b,
  green: 0x4caf50,
  blue: 0x4285f4,
  pink: 0xec4899,
  gray: 0x607d8b,
};

interface Sprite {
  container: Container;
  tileX: number;
  tileY: number;
  px: number;
  py: number;
  path: Tile[];
  isMe: boolean;
}

export function OfficeCanvas({ scene, myAvatar }: { scene: Scene; myAvatar: OfficeAvatar | null }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const sprites = useRef<Map<string, Sprite>>(new Map());
  const entitiesRef = useRef<Container | null>(null);
  const originRef = useRef({ x: 0, y: 0 });
  const moveRef = useRef<(x: number, y: number) => void>(() => {});
  const makeSpriteRef = useRef<(id: string, x: number, y: number, name: string, color: string, kind: string, isMe: boolean) => void>(
    () => {}
  );

  const me: OfficeMe | null = myAvatar
    ? { avatar_id: myAvatar.id, name: myAvatar.name, color: myAvatar.color, kind: "user", x: myAvatar.home_x, y: myAvatar.home_y }
    : null;

  // Posiciona/atualiza alvo de um avatar remoto (presença).
  const setRemoteTarget = (id: string, x: number, y: number, name?: string, color?: string, kind?: string) => {
    const s = sprites.current.get(id);
    if (s) {
      s.path = [{ x, y }];
    } else {
      makeSpriteRef.current(id, x, y, name || "", color || "gray", kind || "user", false);
    }
  };

  const { connected, move } = useOfficeSocket(scene.id, me, {
    onSnapshot: (list) => list.forEach((e) => setRemoteTarget(e.avatar_id, e.x, e.y, e.name, e.color, e.kind)),
    onEnter: (e) => setRemoteTarget(e.avatar_id, e.x, e.y, e.name, e.color, e.kind),
    onMove: (e) => setRemoteTarget(e.avatar_id, e.x, e.y, e.name, e.color, e.kind),
    onLeave: (id) => {
      const s = sprites.current.get(id);
      if (s && !s.isMe) {
        s.container.destroy();
        sprites.current.delete(id);
      }
    },
  });
  moveRef.current = move;

  useEffect(() => {
    let destroyed = false;
    const blocked = new Set<string>();

    (async () => {
      const PIXI = await import("pixi.js");
      if (destroyed || !mountRef.current) return;

      const width = Math.max(640, (scene.grid_width + scene.grid_height) * (TILE_W / 2));
      const height = (scene.grid_width + scene.grid_height) * (TILE_H / 2) + 160;

      const app = new PIXI.Application();
      await app.init({ width, height, background: 0xf3ece0, antialias: true });
      if (destroyed) {
        app.destroy(true);
        return;
      }
      appRef.current = app;
      mountRef.current.innerHTML = "";
      mountRef.current.appendChild(app.canvas);

      const originX = width / 2;
      const originY = 70;
      originRef.current = { x: originX, y: originY };

      // ---- piso ----
      const floor = new PIXI.Graphics();
      for (let y = 0; y < scene.grid_height; y++) {
        for (let x = 0; x < scene.grid_width; x++) {
          const { sx, sy } = isoToScreen(x, y, originX, originY);
          const shade = (x + y) % 2 === 0 ? 0xe7d9c4 : 0xefe6d6;
          floor
            .poly([sx, sy - TILE_H / 2, sx + TILE_W / 2, sy, sx, sy + TILE_H / 2, sx - TILE_W / 2, sy])
            .fill({ color: shade })
            .stroke({ width: 1, color: 0xdac9b0 });
        }
      }
      app.stage.addChild(floor);

      // ---- móveis ----
      const catalog = new Map(scene.catalog.map((c) => [c.code, c]));
      const furniture = new PIXI.Container();
      furniture.sortableChildren = true;
      for (const p of scene.furniture) {
        const item = catalog.get(p.furniture_code);
        if (!item) continue;
        const { sx, sy } = isoToScreen(p.x, p.y, originX, originY);
        const g = new PIXI.Graphics();
        g.poly([sx, sy - TILE_H / 2, sx + TILE_W / 2, sy, sx, sy + TILE_H / 2, sx - TILE_W / 2, sy])
          .fill({ color: parseInt(item.color.replace("#", "0x")) });
        const icon = new PIXI.Text({ text: item.icon, style: { fontSize: 20 } });
        icon.anchor.set(0.5);
        icon.position.set(sx, sy - 6);
        const fc = new PIXI.Container();
        fc.addChild(g, icon);
        fc.zIndex = p.x + p.y;
        furniture.addChild(fc);
        if (!item.walkable) {
          for (let dx = 0; dx < item.width; dx++)
            for (let dy = 0; dy < item.depth; dy++) blocked.add(key(p.x + dx, p.y + dy));
        }
      }
      app.stage.addChild(furniture);

      // ---- avatares ----
      const entities = new PIXI.Container();
      entities.sortableChildren = true;
      entitiesRef.current = entities;
      app.stage.addChild(entities);

      const makeSprite = (id: string, x: number, y: number, name: string, color: string, kind: string, isMe: boolean) => {
        const c = new PIXI.Container();
        const shadow = new PIXI.Graphics();
        shadow.ellipse(0, 6, 14, 7).fill({ color: 0x000000, alpha: 0.15 });
        const body = new PIXI.Graphics();
        body.circle(0, -6, 13).fill({ color: COLOR_HEX[color] ?? COLOR_HEX.gray });
        const emoji = new PIXI.Text({ text: kind === "agent" ? "🐹" : "🧑", style: { fontSize: 15 } });
        emoji.anchor.set(0.5);
        emoji.position.set(0, -6);
        const label = new PIXI.Text({
          text: name + (isMe ? " (você)" : ""),
          style: { fontSize: 10, fill: 0x2c2924 },
        });
        label.anchor.set(0.5);
        label.position.set(0, 12);
        c.addChild(shadow, body, emoji, label);
        const { sx, sy } = isoToScreen(x, y, originRef.current.x, originRef.current.y);
        c.position.set(sx, sy);
        entities.addChild(c);
        sprites.current.set(id, { container: c, tileX: x, tileY: y, px: sx, py: sy, path: [], isMe });
      };
      makeSpriteRef.current = makeSprite;

      // cria sprites iniciais a partir da cena (admin + agentes)
      for (const av of scene.avatars) {
        const isMe = av.id === myAvatar?.id;
        makeSprite(av.id, av.home_x, av.home_y, av.name, av.color, av.owner_kind, isMe);
      }

      // ---- clique no piso → caminho A* para o meu avatar ----
      app.stage.eventMode = "static";
      app.stage.hitArea = new PIXI.Rectangle(0, 0, width, height);
      app.stage.on("pointertap", (e: { global: { x: number; y: number } }) => {
        if (!myAvatar) return;
        const ms = sprites.current.get(myAvatar.id);
        if (!ms) return;
        const t = screenToIso(e.global.x, e.global.y, originRef.current.x, originRef.current.y);
        if (t.x < 0 || t.y < 0 || t.x >= scene.grid_width || t.y >= scene.grid_height) return;
        if (blocked.has(key(t.x, t.y))) return;
        const path = findPath({ x: ms.tileX, y: ms.tileY }, t, scene.grid_width, scene.grid_height, blocked);
        if (path.length) ms.path = path;
      });

      // ---- loop de animação ----
      app.ticker.add((ticker) => {
        const dt = ticker.deltaTime;
        const lerp = Math.min(1, 0.18 * dt);
        for (const s of sprites.current.values()) {
          const tgt = s.path.length ? s.path[0] : { x: s.tileX, y: s.tileY };
          const { sx, sy } = isoToScreen(tgt.x, tgt.y, originRef.current.x, originRef.current.y);
          s.px += (sx - s.px) * lerp;
          s.py += (sy - s.py) * lerp;
          s.container.position.set(s.px, s.py);
          s.container.zIndex = tgt.x + tgt.y;
          if (Math.hypot(sx - s.px, sy - s.py) < 1.5 && s.path.length) {
            s.tileX = tgt.x;
            s.tileY = tgt.y;
            s.path.shift();
            if (s.isMe) moveRef.current(s.tileX, s.tileY);
          }
        }
      });
    })();

    return () => {
      destroyed = true;
      sprites.current.clear();
      entitiesRef.current = null;
      appRef.current?.destroy(true, { children: true });
      appRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene.id, myAvatar?.id]);

  return (
    <div className="relative">
      <div
        ref={mountRef}
        className="overflow-auto rounded-xl border border-sand-200 bg-sand-100 shadow-soft"
      />
      <div className="absolute right-3 top-3 rounded-full bg-white/80 px-3 py-1 text-xs">
        {connected ? "🟢 online" : "🟡 conectando"} · clique no piso para andar
      </div>
    </div>
  );
}
