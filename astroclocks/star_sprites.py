import math
from dataclasses import dataclass


DEFAULT_STAR_RADIUS_BINS = (1, 2, 3, 4, 5, 6, 8, 9, 12, 18)
DEFAULT_STAR_ALPHA_BINS = (40, 56, 72, 88, 104, 120, 144, 168, 192, 216, 240, 255)


@dataclass(frozen=True)
class StarRenderStyle:
    fill: str
    rgb: tuple[int, int, int]
    radius_px: int
    alpha: int
    sprite: object
    canvas_size: float


@dataclass(frozen=True)
class StarRenderStats:
    considered: int = 0
    projected: int = 0
    drawn: int = 0
    render_ms: float = 0.0
    sprite_cache_size: int = 0


class StarSpriteCache:
    """Precomputed radial star sprites for CPU/PIL sky-map rendering.

    Magnitude is mapped perceptually with q = clamp((m_lim - m) /
    (m_lim - m_bright), 0, 1). The sprite radius uses gamma_radius and
    opacity uses gamma_alpha plus brightness_multiplier. Radial masks use
    a double gaussian profile: 0.85 * exp(-6 r^2) + 0.15 * exp(-1.5 r^2),
    sampled once per radius bin.
    """

    def __init__(
        self,
        image_module,
        *,
        radius_bins=DEFAULT_STAR_RADIUS_BINS,
        alpha_bins=DEFAULT_STAR_ALPHA_BINS,
        magnitude_limit=6.5,
        bright_magnitude=-1.5,
        min_radius=1.6,
        max_radius=8.0,
        gamma_radius=1.8,
        gamma_alpha=1.3,
        min_alpha=0.27,
        max_alpha=1.0,
        brightness_multiplier=1.0,
    ):
        self.image_module = image_module
        self.radius_bins = tuple(sorted(int(radius) for radius in radius_bins))
        self.alpha_bins = tuple(sorted(int(alpha) for alpha in alpha_bins))
        self.magnitude_limit = float(magnitude_limit)
        self.bright_magnitude = float(bright_magnitude)
        self.min_radius = float(min_radius)
        self.max_radius = float(max_radius)
        self.gamma_radius = float(gamma_radius)
        self.gamma_alpha = float(gamma_alpha)
        self.min_alpha = float(min_alpha)
        self.max_alpha = float(max_alpha)
        self.brightness_multiplier = float(brightness_multiplier)
        self._mask_cache = {}
        self._sprite_cache = {}
        self._style_cache = {}
        self._build_alpha_masks()

    def configure(self, *, magnitude_limit=None):
        if magnitude_limit is None:
            return
        magnitude_limit = float(magnitude_limit)
        if round(magnitude_limit, 4) == round(self.magnitude_limit, 4):
            return
        self.magnitude_limit = magnitude_limit
        self._style_cache.clear()

    @property
    def sprite_count(self):
        return len(self._sprite_cache)

    def style_for(self, fill, rgb, magnitude):
        magnitude_key = round(float(magnitude), 2)
        key = (fill, tuple(rgb), magnitude_key, round(self.magnitude_limit, 2))
        cached = self._style_cache.get(key)
        if cached is not None:
            return cached

        radius, alpha = self._map_magnitude(magnitude_key)
        radius = self._nearest_bin(radius, self.radius_bins)
        alpha = self._nearest_bin(alpha, self.alpha_bins)
        sprite = self.sprite_for(rgb, radius, alpha)
        style = StarRenderStyle(
            fill=fill,
            rgb=tuple(rgb),
            radius_px=radius,
            alpha=alpha,
            sprite=sprite,
            canvas_size=max(1.2, radius * 0.72),
        )
        self._style_cache[key] = style
        return style

    def sprite_for(self, rgb, radius, alpha):
        radius = self._nearest_bin(radius, self.radius_bins)
        alpha = self._nearest_bin(alpha, self.alpha_bins)
        key = (tuple(rgb), int(radius), int(alpha))
        cached = self._sprite_cache.get(key)
        if cached is not None:
            return cached

        mask = self._scaled_alpha_mask(radius, alpha)
        size = mask.size
        red, green, blue = rgb
        sprite = self.image_module.new("RGBA", size, (red, green, blue, 0))
        sprite.putalpha(mask)
        self._sprite_cache[key] = sprite
        return sprite

    def composite_sprite(self, target, sprite, center_x, center_y):
        sprite_width, sprite_height = sprite.size
        width, height = target.size
        left = int(round(center_x - sprite_width / 2))
        top = int(round(center_y - sprite_height / 2))
        right = left + sprite_width
        bottom = top + sprite_height
        if right <= 0 or bottom <= 0 or left >= width or top >= height:
            return False

        paste_x = max(0, left)
        paste_y = max(0, top)
        paste_right = min(width, right)
        paste_bottom = min(height, bottom)
        if paste_x == left and paste_y == top and paste_right == right and paste_bottom == bottom:
            target.alpha_composite(sprite, (left, top))
            return True

        cropped = sprite.crop(
            (
                paste_x - left,
                paste_y - top,
                paste_right - left,
                paste_bottom - top,
            )
        )
        target.alpha_composite(cropped, (paste_x, paste_y))
        return True

    def _map_magnitude(self, magnitude):
        denominator = max(0.1, self.magnitude_limit - self.bright_magnitude)
        q = max(0.0, min(1.0, (self.magnitude_limit - magnitude) / denominator))
        radius = self.min_radius + (self.max_radius - self.min_radius) * (q**self.gamma_radius)
        alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * (q**self.gamma_alpha)
        return radius, min(255, round(255 * alpha * self.brightness_multiplier))

    def _build_alpha_masks(self):
        for radius in self.radius_bins:
            self._mask_cache[(radius, 255)] = self._radial_alpha_mask(radius)

    def _radial_alpha_mask(self, radius):
        diameter = radius * 2 + 1
        center = radius + 0.5
        pixels = bytearray(diameter * diameter)
        offset = 0
        for y in range(diameter):
            dy = (y + 0.5 - center) / max(1, radius)
            for x in range(diameter):
                dx = (x + 0.5 - center) / max(1, radius)
                r_sq = dx * dx + dy * dy
                if r_sq > 1.0:
                    value = 0
                else:
                    intensity = 0.85 * math.exp(-6.0 * r_sq) + 0.15 * math.exp(-1.5 * r_sq)
                    value = int(255 * intensity)
                pixels[offset] = value
                offset += 1
        return self.image_module.frombytes("L", (diameter, diameter), bytes(pixels))

    def _scaled_alpha_mask(self, radius, alpha):
        key = (int(radius), int(alpha))
        cached = self._mask_cache.get(key)
        if cached is not None:
            return cached

        base = self._mask_cache[(int(radius), 255)]
        scale = int(alpha) / 255
        mask = base.point(lambda value: int(value * scale))
        self._mask_cache[key] = mask
        return mask

    @staticmethod
    def _nearest_bin(value, bins):
        return min(bins, key=lambda candidate: abs(candidate - value))
