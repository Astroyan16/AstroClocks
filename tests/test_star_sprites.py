import unittest

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised only without Pillow installed.
    Image = None

from astroclocks.star_sprites import StarSpriteCache


@unittest.skipIf(Image is None, "Pillow is required for sprite-cache tests")
class StarSpriteCacheTests(unittest.TestCase):
    def test_empty_target_can_be_created_without_sprites(self):
        cache = StarSpriteCache(Image)
        target = Image.new("RGBA", (32, 24), (0, 0, 0, 0))

        self.assertEqual(target.size, (32, 24))
        self.assertEqual(cache.sprite_count, 0)

    def test_offscreen_sprite_is_ignored_without_error(self):
        cache = StarSpriteCache(Image)
        sprite = cache.style_for("#ffffff", (255, 255, 255), 1.0).sprite
        target = Image.new("RGBA", (32, 24), (0, 0, 0, 0))

        self.assertFalse(cache.composite_sprite(target, sprite, -50, -50))

    def test_extreme_magnitudes_are_clamped_to_visual_bins(self):
        cache = StarSpriteCache(Image)

        bright = cache.style_for("#ffffff", (255, 255, 255), -10.0)
        faint = cache.style_for("#ffffff", (255, 255, 255), 20.0)

        self.assertGreaterEqual(bright.radius_px, faint.radius_px)
        self.assertGreaterEqual(bright.alpha, faint.alpha)
        self.assertEqual(bright.radius_px, 8)
        self.assertEqual(faint.radius_px, 2)

    def test_sprite_cache_reuses_existing_sprite(self):
        cache = StarSpriteCache(Image)

        first = cache.style_for("#d7eaff", (215, 234, 255), 2.14)
        count_after_first = cache.sprite_count
        second = cache.style_for("#d7eaff", (215, 234, 255), 2.14)

        self.assertIs(first.sprite, second.sprite)
        self.assertEqual(cache.sprite_count, count_after_first)

    def test_magnitude_limit_change_invalidates_style_mapping_only(self):
        cache = StarSpriteCache(Image)

        before = cache.style_for("#ffffff", (255, 255, 255), 5.8)
        sprite_count = cache.sprite_count
        cache.configure(magnitude_limit=4.0)
        after = cache.style_for("#ffffff", (255, 255, 255), 5.8)

        self.assertEqual(cache.magnitude_limit, 4.0)
        self.assertLessEqual(after.alpha, before.alpha)
        self.assertGreaterEqual(cache.sprite_count, sprite_count)


if __name__ == "__main__":
    unittest.main()
