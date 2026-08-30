"""灵体层 · 徙居系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 徙居Mixin:
    """灵之徙居诸行。"""

    # ── 逃荒与迁徙（v6.4）：故土资源崩溃 → 弃家携眷，迁往丰饶 ──

    def _察荒(self, world: World, spirits: list, tick: int, report, rng):
        """每日一次打量故土：居所四周草枯水涸积够三日，便生弃家迁徙之念。"""
        day = tick // TICKS_PER_DAY
        if self._荒_day == day or is_night(tick) or self._迁 is not None:
            return
        self._荒_day = day
        hy, hx = self._栖身所()
        if self._切比(self.y, self.x, hy, hx) > 6:
            return
        r = 4
        草, 水 = [], False
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                ny, nx = hy + dy, hx + dx
                if world.in_bounds(ny, nx):
                    草.append(world.grass[ny, nx])
                    if world.water[ny, nx] >= DRINK_MIN:
                        水 = True
        # 井也是水：近处有井，故土不算涸——凿井真能安住人心
        if not 水:
            for (wy, wx) in self._known_wells:
                if world.well_at(wy, wx) is not None \
                        and self._切比(hy, hx, wy, wx) <= r:
                    水 = True
                    break
        if 草 and sum(草) / len(草) < FAMINE_GRASS and not 水:
            self._荒 += 1
        else:
            self._荒 = 0
        if self._荒 >= FAMINE_DAYS and self.yang > 45.0:
            self._起迁(world, spirits, tick, report, rng)

    def _起迁(self, world: World, spirits: list, tick: int, report, rng):
        """弃家携眷，迁往丰饶处（记忆中最新的远处食点；无则望一个方向闯出去）。
        不动产尽弃：屋田栏火留作无主遗迹——门楣之名犹在，物是人非。"""
        远处 = [(t, p) for p, t in self.known_food.items()
                if self._切比(self.y, self.x, p[0], p[1]) >= MIGRATE_NEAR]
        if 远处:
            远处.sort()
            ty, tx = 远处[-1][1]
        else:
            向 = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            d = 向[rng.randrange(8)]
            ty = int(max(0, min(world.size - 1, self.y + d[0] * 14)))
            tx = int(max(0, min(world.size - 1, self.x + d[1] * 14)))
        self._迁 = (ty, tx, tick)
        self._迁由 = "故土草枯水涸"
        self._荒 = 0
        故居 = (self.y, self.x)
        self._弃产(world)
        # 携眷：伴侣同行，稚子自会跟着父母
        眷 = next((s for s in spirits if s.alive and s.name == self.伴侣), None)
        if 眷 is not None and 眷._迁 is None:
            眷._迁 = (ty, tx, tick)
            眷._迁由 = f"随 {self.name} 举家而迁"
            眷._荒 = 0
            眷._弃产(world)
            眷.remember(f"随 {self.name} 弃家而迁", "迁徙", self.name, 0.60, tick)
        携 = f"携 {眷.name} " if 眷 is not None else ""
        self.remember("弃家而迁，故土难留", "迁徙", None, 0.65, tick)
        report(tick, 故居,
               f"{self.name} {携}弃宅而去，踏上迁徙之路（因：{self._迁由}）",
               kind="迁徙", actor=self.name, target=眷.name if 眷 else None)

    def _弃产(self, world: World):
        """丢弃不动产：屋留原地风雨飘摇，田栏火改称"荒"，牲畜野化。"""
        self.hut = None       # 屋成无主遗迹，门楣之名犹在
        self._家门 = None
        self._工地 = None
        self._井地 = None
        for f in world.farms:
            if f.主人 == self.name:
                f.主人 = "荒"
        for f in world.fences:
            if f.主人 == self.name:
                f.主人 = "荒"
        for f in world.fires:
            if f.主人 == self.name:
                f.主人 = "荒"
        for a in world.animals:
            if a.驯主 == self.name:
                a.驯主 = None
                a.栏位 = None

    def _行迁(self, world: World, tick: int, report, rng) -> bool:
        """迁徙途中：昼行夜宿，不到新土不止；抵达或跋涉太久则落脚。"""
        ty, tx, 起 = self._迁
        到 = self._切比(self.y, self.x, ty, tx) <= 2
        疲 = tick - 起 > MIGRATE_GIVEUP * TICKS_PER_DAY
        if 到 or 疲:
            self._迁 = None
            self._stay = {}     # 落脚新土，栖身所重新长出来
            self._荒 = -2       # 初到之地休养生息两日，再打量故土荒否
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.2)
            注 = "寻得新土" if 到 else "跋涉力竭，就地落脚"
            report(tick, (self.y, self.x),
                   f"{self.name} 迁抵{world.terrain_name(self.y, self.x)}，于此重建家园"
                   f"（因：{self._迁由}+{注}）",
                   kind="迁抵", actor=self.name)
            return False        # 落脚的这一念，余下时光照常过
        self._走向(world, ty, tx, rng)
        return True
