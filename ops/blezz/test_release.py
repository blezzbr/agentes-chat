import unittest

from release import next_tag, upstream_range


def upstream_release(tag):
    return {"tag_name": tag, "body": f"Official notes for {tag}"}


class ReleaseTests(unittest.TestCase):
    def test_first_revision_and_same_base_increment(self):
        self.assertEqual(next_tag(["blezz-v1.0.0"], "0.1.18"), "blezz-v0.1.18-r1")
        self.assertEqual(
            next_tag(["blezz-v0.1.18-r2", "blezz-v0.1.18-r10"], "0.1.18"),
            "blezz-v0.1.18-r11",
        )

    def test_new_base_resets_revision_and_regression_is_rejected(self):
        tags = ["blezz-v0.1.18-r7"]
        self.assertEqual(next_tag(tags, "0.1.23"), "blezz-v0.1.23-r1")
        with self.assertRaises(ValueError):
            next_tag(tags, "0.1.17")

    def test_every_published_server_release_in_the_range(self):
        releases = list(map(upstream_release, [
            "v0.1.18", "v0.1.17", "desktop-v0.8.19", "v0.1.15", "v0.1.14",
            "v0.1.13", "v0.1.19",
        ]))
        result = upstream_range(releases, "0.1.13", "0.1.18")
        self.assertEqual([r["tag_name"] for r in result], [
            "v0.1.14", "v0.1.15", "v0.1.17", "v0.1.18",
        ])
        self.assertEqual(upstream_range(releases, "0.1.18", "0.1.18"), [])
        with self.assertRaises(ValueError):
            upstream_range(releases, "0.1.13", "0.1.16")


if __name__ == "__main__":
    unittest.main()
