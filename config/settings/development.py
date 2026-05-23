DEBUG = True

INSTALLED_APPS_EXTRA = []

REST_FRAMEWORK_EXTRA = {
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}
