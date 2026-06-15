from pydantic import BaseModel


class FurnitureCatalogOut(BaseModel):
    code: str
    name: str
    category: str
    width: int
    depth: int
    color: str
    icon: str
    walkable: bool


class PlacementOut(BaseModel):
    id: str
    furniture_code: str
    x: int
    y: int
    rotation: int


class AvatarOut(BaseModel):
    id: str
    owner_kind: str
    owner_id: str
    name: str
    color: str
    home_x: int
    home_y: int


class SceneOut(BaseModel):
    id: str
    name: str
    grid_width: int
    grid_height: int
    theme: str
    furniture: list[PlacementOut]
    avatars: list[AvatarOut]
    catalog: list[FurnitureCatalogOut]
    presence: list[dict]


class PlaceFurnitureIn(BaseModel):
    furniture_code: str
    x: int
    y: int
    rotation: int = 0


class AppearanceIn(BaseModel):
    appearance: dict
