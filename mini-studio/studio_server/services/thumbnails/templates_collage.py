"""Collage family (DeByte podcast style): a wall of magazine covers made from the news images
(found by Claude Code from your list of news), warped and scattered, and you in black and white in
the middle. No logos and no title: the only text is on the magazines."""

COLLAGE_TEMPLATES = {
    "collage_magazines": {
        "max_chars": 60,  # the title isn't drawn
        "description": "Wall of warped magazine covers from your news list, you in black and white in the middle "
                       "(no logos, no title)",
        "defaults": {"color": "blue"},
        "needs": ["news"],  # the Studio shows the news list for this one
        "base": "#141018",
        "ops": [
            # only the news pictures: no background photo (placeholder) and no shade over the covers
            {"op": "magazines", "cols": 5, "rows": 2, "extra": 3, "scale": 0.92},
            {"op": "person", "x": 640, "top": 40, "height": 1080, "outline": 0, "desaturate": True,
             "shadow": True},
        ],
    },
}
