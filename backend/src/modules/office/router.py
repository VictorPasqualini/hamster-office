from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.deps import TenantCtx, tenant_ctx
from ...core.exceptions import NotFound
from ...core.realtime import publish_event
from ...db.models import (
    Agent,
    Avatar,
    FurnitureCatalog,
    FurniturePlacement,
    Membership,
    OfficeScene,
    User,
)
from .schemas import (
    AppearanceIn,
    AvatarOut,
    FurnitureCatalogOut,
    PlaceFurnitureIn,
    PlacementOut,
    SceneOut,
)
from .service import get_presence

router = APIRouter(prefix="/office", tags=["office"])


async def _resolve_scene(ctx: TenantCtx) -> OfficeScene:
    scene = await ctx.db.scalar(
        select(OfficeScene).where(OfficeScene.workspace_id == ctx.workspace_id).limit(1)
    )
    if not scene:
        scene = OfficeScene(workspace_id=ctx.workspace_id, name="Escritório")
        ctx.db.add(scene)
        await ctx.db.flush()
    return scene


async def _avatars(ctx: TenantCtx) -> list[AvatarOut]:
    avatars = list(await ctx.db.scalars(select(Avatar).where(Avatar.workspace_id == ctx.workspace_id)))
    # mapas de nome/cor
    user_names: dict = {}
    rows = await ctx.db.execute(
        select(Membership.id, User.name).join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == ctx.workspace_id)
    )
    for mid, name in rows.all():
        user_names[str(mid)] = name
    agents = {
        str(a.id): a
        for a in await ctx.db.scalars(select(Agent).where(Agent.workspace_id == ctx.workspace_id))
    }
    out = []
    for av in avatars:
        oid = str(av.owner_id)
        if av.owner_kind == "agent":
            ag = agents.get(oid)
            name = ag.name if ag else "Agente"
            color = (ag.appearance.get("color") if ag and ag.appearance else None) or "orange"
        else:
            name = user_names.get(oid, "Usuário")
            color = (av.appearance.get("color") if av.appearance else None) or "gray"
        out.append(
            AvatarOut(
                id=str(av.id),
                owner_kind=av.owner_kind,
                owner_id=oid,
                name=name,
                color=color,
                home_x=av.home_x,
                home_y=av.home_y,
            )
        )
    return out


@router.get("/scene", response_model=SceneOut)
async def get_scene(ctx: TenantCtx = Depends(tenant_ctx)):
    scene = await _resolve_scene(ctx)
    placements = await ctx.db.scalars(
        select(FurniturePlacement).where(FurniturePlacement.scene_id == scene.id)
    )
    catalog = await ctx.db.scalars(select(FurnitureCatalog))
    return SceneOut(
        id=str(scene.id),
        name=scene.name,
        grid_width=scene.grid_width,
        grid_height=scene.grid_height,
        theme=scene.theme,
        furniture=[
            PlacementOut(id=str(p.id), furniture_code=p.furniture_code, x=p.x, y=p.y, rotation=p.rotation)
            for p in placements
        ],
        avatars=await _avatars(ctx),
        catalog=[FurnitureCatalogOut.model_validate(c, from_attributes=True) for c in catalog],
        presence=await get_presence(str(ctx.workspace_id), str(scene.id)),
    )


@router.get("/furniture-catalog", response_model=list[FurnitureCatalogOut])
async def furniture_catalog(ctx: TenantCtx = Depends(tenant_ctx)):
    rows = await ctx.db.scalars(select(FurnitureCatalog))
    return [FurnitureCatalogOut.model_validate(c, from_attributes=True) for c in rows]


@router.post("/furniture", response_model=PlacementOut, status_code=201)
async def place_furniture(body: PlaceFurnitureIn, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("manager")
    scene = await _resolve_scene(ctx)
    p = FurniturePlacement(
        workspace_id=ctx.workspace_id,
        scene_id=scene.id,
        furniture_code=body.furniture_code,
        x=body.x,
        y=body.y,
        rotation=body.rotation,
    )
    ctx.db.add(p)
    await ctx.db.flush()
    out = PlacementOut(id=str(p.id), furniture_code=p.furniture_code, x=p.x, y=p.y, rotation=p.rotation)
    await publish_event(f"office:{scene.id}", "office.furniture.placed", out.model_dump())
    return out


@router.delete("/furniture/{placement_id}", status_code=204)
async def remove_furniture(placement_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("manager")
    p = await ctx.db.scalar(select(FurniturePlacement).where(FurniturePlacement.id == placement_id))
    if not p:
        raise NotFound("Móvel não encontrado")
    scene_id = p.scene_id
    await ctx.db.delete(p)
    await publish_event(f"office:{scene_id}", "office.furniture.removed", {"id": placement_id})


@router.get("/avatars/me", response_model=AvatarOut)
async def my_avatar(ctx: TenantCtx = Depends(tenant_ctx)):
    av = await ctx.db.scalar(
        select(Avatar).where(
            Avatar.workspace_id == ctx.workspace_id,
            Avatar.owner_kind == "user",
            Avatar.owner_id == ctx.membership_id,
        )
    )
    if not av:
        av = Avatar(
            workspace_id=ctx.workspace_id,
            owner_kind="user",
            owner_id=ctx.membership_id,
            appearance={"color": "gray"},
            home_x=3,
            home_y=5,
        )
        ctx.db.add(av)
        await ctx.db.flush()
    return AvatarOut(
        id=str(av.id),
        owner_kind="user",
        owner_id=str(av.owner_id),
        name=ctx.user.name,
        color=(av.appearance.get("color") if av.appearance else None) or "gray",
        home_x=av.home_x,
        home_y=av.home_y,
    )


@router.put("/avatars/{avatar_id}/appearance", status_code=204)
async def update_appearance(avatar_id: str, body: AppearanceIn, ctx: TenantCtx = Depends(tenant_ctx)):
    av = await ctx.db.scalar(select(Avatar).where(Avatar.id == avatar_id))
    if not av:
        raise NotFound("Avatar não encontrado")
    av.appearance = body.appearance
